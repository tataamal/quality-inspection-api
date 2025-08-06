# Akan diisi terpisah karena sangat panjangfrom flask import Blueprint, request, jsonify, make_response
from flask import Blueprint, request, jsonify
import mysql.connector
from flask import make_response
from app.services.sap_service import connect_sap
from app.utils.helpers import parse_date
import mysql.connector
import traceback
from config import db_config
from datetime import datetime, date

sap_bp = Blueprint('sap_bp', __name__)

@sap_bp.route('/api/sap-login', methods=['POST'])
def sap_login():

    data = request.json
    username = data['username']
    password = data['password']

    print(username)
    print(password)

    # # return print(username, password)

    # try:
    #     conn = connect_sap(username, password)
    #     conn.ping()
    #     print("[SUCCESS] Login sukses!")
    #     return jsonify({'status': 'connected', 'username' : username, 'password' : password})
    # except Exception as e:
    #     print("[ERROR] SAP Login failed:", str(e))
    #     return jsonify({'error': str(e)}), 401
    
@sap_bp.route('/api/send_usage_decision', methods=['POST'])
def send_usage_decision():
    try:
        # Ambil data dari request
        data = request.json
        username = data.get('username')
        password = data.get('password')
        conn = connect_sap(username, password)

        # Input utama
        prueflos = data.get('prueflos')
        plant = data.get('plant')
        ud_selected_set = data.get('ud_selected_set')
        ud_code_group = data.get('ud_code_group')
        ud_code = data.get('ud_code')
        stock_posting = data.get('stock_posting')

        # Kirim Usage Decision ke SAP
        ud_response = conn.call('Z_RFC_UD_RECEIVE_PY',  
            IV_NUMBER=prueflos,
            IV_UD_SELECTED_SET=ud_selected_set,
            IV_UD_PLANT=plant,
            IV_UD_CODE_GROUP=ud_code_group,
            IV_UD_CODE=ud_code,
            IV_RECORDED_BY_USER=username,
            IV_RECORDED_ON_DATE=date.today().strftime('%Y%m%d'),
            IV_RECORDED_AT_TIME=datetime.now().strftime('%H%M%S'),
            IV_STOCK_POSTING=stock_posting
        )

        # Commit ke SAP
        conn.call('BAPI_TRANSACTION_COMMIT', WAIT='X')

        # Ambil respons
        ud_msg = ud_response.get("EV_MESSAGE", "No message returned")
        subrc = ud_response.get("EV_SUBRC", "")
        ud_success = (str(subrc) == '0')

        # Kirim feedback ke Laravel/frontend
        return make_response(jsonify({
            "status": "success" if ud_success else "error",
            "message": ud_msg,
            "usage_decision": {
                "message": ud_msg,
                "subrc": subrc,
                "success": ud_success
            }
        }), 200)

    except Exception as e:
        import traceback
        print("SAP UD ERROR:", e)
        traceback.print_exc()
        return make_response(jsonify({
            "status": "error",
            "message": f"Exception saat kirim ke SAP: {str(e)}",
            "trace": traceback.format_exc()
        }), 500)
    
@sap_bp.route('/api/good_movement_344', methods=['POST'])
def push_good_movement():
    try:
        # Ambil data dari request
        data = request.json
        username = data.get('username')
        password = data.get('password')
        conn = connect_sap(username, password)

        # Ambil field
        material = data.get('material')
        plant = data.get('plant')
        stge_loc = data.get('stge_loc')
        batch = data.get('charg')
        move_type = '344'
        sales_order = data.get('kdauf', '')
        so_item = data.get('kdpos')
        reject = data.get('reject', 0)
        uom = data.get('entry_uom')
        post_date = date.today().strftime('%Y%m%d')
        doc_date = date.today().strftime('%Y%m%d')

        # Call Z function to post goods movement
        tp_response = conn.call('Z_RFC_GOODSMVT_PYCHAR',
            IV_MATERIAL=material,
            IV_PLANT='3000',
            IV_STGE_LOC=stge_loc,
            IV_BATCH=batch,
            IV_MOVE_TYPE=move_type,
            IV_SALES_ORD=sales_order,
            IV_S_ORD_ITEM=so_item,
            IV_ENTRY_QTY_CHAR=reject,
            IV_ENTRY_UOM=uom,
            IV_REF_DOC_NO='',
            IV_POST_DATE=post_date,
            IV_DOC_DATE=doc_date
        )

        # Commit to SAP
        conn.call('BAPI_TRANSACTION_COMMIT', WAIT='X')

        # Return hasil
        result = {
            "status": "success",
            "material_doc": tp_response.get("EV_MATERIAL_DOC"),
            "message": tp_response.get("EV_MESSAGE")
        }
        return jsonify(result), 200

    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500
    
@sap_bp.route('/api/get_insp_lot', methods=['GET'])
def get_insp_lot():
    plant = request.args.get('plant')
    username = request.args.get('username')
    password = request.args.get('password')

    if not plant:
        return jsonify({"error": "Parameter 'plant' is required"}), 400

    try:
        # Koneksi ke SAP
        conn = connect_sap(username, password)

        # Ambil data dari SAP
        result = conn.call('Z_RFC_GET_INSP_LOT_BY_DISPO2', IV_WERKS=plant)
        data = result.get('ET_QALS', [])

        # Koneksi ke MySQL
        conn_mysql = mysql.connector.connect(
            host="localhost",
            user="root",
            password="",
            database="quality_inspection"
        )
        cursor = conn_mysql.cursor()

        # Hapus data lama untuk plant tersebut
        cursor.execute("DELETE FROM quality_inspection_lots WHERE WERK = %s", (plant,))

        # Simpan data baru
        for lot in data:
            values = {
                'PRUEFLOS': lot.get('PRUEFLOS'),
                'WERK': lot.get('WERK'),
                'ART': lot.get('ART'),
                'HERKUNFT': lot.get('HERKUNFT'),
                'OBJNR': lot.get('OBJNR'),
                'ENSTEHDAT': parse_date(lot.get('ENSTEHDAT')),
                'ENTSTEZEIT': lot.get('ENTSTEZEIT'),
                'AUFNR': lot.get('AUFNR'),
                'DISPO': lot.get('DISPO'),
                'ARBPL': lot.get('ARBPL'),
                'KTEXT': lot.get('KTEXT'),
                'ARBID': lot.get('ARBID'),
                'KUNNR': lot.get('KUNNR'),
                'LIFNR': lot.get('LIFNR'),
                'HERSTELLER': lot.get('HERSTELLER'),
                'EMATNR': lot.get('EMATNR'),
                'MATNR': lot.get('MATNR'),
                'CHARG': lot.get('CHARG'),
                'LAGORTCHRG': lot.get('LAGORTCHRG'),
                'KDAUF': lot.get('KDAUF'),
                'KDPOS': lot.get('KDPOS'),
                'EBELN': lot.get('EBELN'),
                'EBELP': lot.get('EBELP'),
                'BLART': lot.get('BLART'),
                'MJAHR': lot.get('MJAHR'),
                'MBLNR': lot.get('MBLNR'),
                'ZEILE': lot.get('ZEILE'),
                'BUDAT': parse_date(lot.get('BUDAT')),
                'BWART': lot.get('BWART'),
                'WERKVORG': lot.get('WERKVORG'),
                'LAGORTVORG': lot.get('LAGORTVORG'),
                'LS_KDPOS': lot.get('LS_KDPOS'),
                'LS_VBELN': lot.get('LS_VBELN'),
                'LS_POSNR': lot.get('LS_POSNR'),
                'LS_ROUTE': lot.get('LS_ROUTE'),
                'LS_KUNAG': lot.get('LS_KUNAG'),
                'LS_VKORG': lot.get('LS_VKORG'),
                'LS_KDMAT': lot.get('LS_KDMAT'),
                'SPRACHE': lot.get('SPRACHE'),
                'KTEXTMAT': lot.get('KTEXTMAT'),
                'LOSMENGE': lot.get('LOSMENGE'),
                'MENGENEINH': lot.get('MENGENEINH'),
                'LMENGE01': lot.get('LMENGE01'),
                'LMENGE04': lot.get('LMENGE04'),
                'LMENGE07': lot.get('LMENGE07'),
                'LMENGEZUB': lot.get('LMENGEZUB'),
                'STAT34': lot.get('STAT34'),
                'STAT35': lot.get('STAT35'),
                'KTEXTLOS': lot.get('KTEXTLOS'),
                'INSP_DOC_NUMBER': lot.get('INSP_DOC_NUMBER'),
                'AUFPL': lot.get('AUFPL'),
                'STATS' : lot.get('STATS')
            }

            cursor.execute("""
                INSERT INTO quality_inspection_lots (
                    PRUEFLOS, WERK, ART, HERKUNFT, OBJNR, ENSTEHDAT, ENTSTEZEIT,
                    AUFNR, DISPO, ARBPL, KTEXT, ARBID, KUNNR, LIFNR, HERSTELLER,
                    EMATNR, MATNR, CHARG, LAGORTCHRG, KDAUF, KDPOS, EBELN, EBELP,
                    BLART, MJAHR, MBLNR, ZEILE, BUDAT, BWART, WERKVORG, LAGORTVORG,
                    LS_KDPOS, LS_VBELN, LS_POSNR, LS_ROUTE, LS_KUNAG, LS_VKORG,
                    LS_KDMAT, SPRACHE, KTEXTMAT, LOSMENGE, MENGENEINH, LMENGE01,
                    LMENGE04, LMENGE07, LMENGEZUB, STAT34, STAT35, KTEXTLOS,
                    INSP_DOC_NUMBER, AUFPL, STATS
                ) VALUES (
                    %(PRUEFLOS)s, %(WERK)s, %(ART)s, %(HERKUNFT)s, %(OBJNR)s, %(ENSTEHDAT)s, %(ENTSTEZEIT)s,
                    %(AUFNR)s, %(DISPO)s, %(ARBPL)s, %(KTEXT)s, %(ARBID)s, %(KUNNR)s, %(LIFNR)s, %(HERSTELLER)s,
                    %(EMATNR)s, %(MATNR)s, %(CHARG)s, %(LAGORTCHRG)s, %(KDAUF)s, %(KDPOS)s, %(EBELN)s, %(EBELP)s,
                    %(BLART)s, %(MJAHR)s, %(MBLNR)s, %(ZEILE)s, %(BUDAT)s, %(BWART)s, %(WERKVORG)s, %(LAGORTVORG)s,
                    %(LS_KDPOS)s, %(LS_VBELN)s, %(LS_POSNR)s, %(LS_ROUTE)s, %(LS_KUNAG)s, %(LS_VKORG)s,
                    %(LS_KDMAT)s, %(SPRACHE)s, %(KTEXTMAT)s, %(LOSMENGE)s, %(MENGENEINH)s, %(LMENGE01)s,
                    %(LMENGE04)s, %(LMENGE07)s, %(LMENGEZUB)s, %(STAT34)s, %(STAT35)s, %(KTEXTLOS)s,
                    %(INSP_DOC_NUMBER)s, %(AUFPL)s, %(STATS)s
                )
                ON DUPLICATE KEY UPDATE
                    WERK=VALUES(WERK),
                    ART=VALUES(ART),
                    HERKUNFT=VALUES(HERKUNFT),
                    OBJNR=VALUES(OBJNR),
                    ENSTEHDAT=VALUES(ENSTEHDAT),
                    ENTSTEZEIT=VALUES(ENTSTEZEIT),
                    AUFNR=VALUES(AUFNR),
                    DISPO=VALUES(DISPO),
                    ARBPL=VALUES(ARBPL),
                    KTEXT=VALUES(KTEXT),
                    ARBID=VALUES(ARBID),
                    KUNNR=VALUES(KUNNR),
                    LIFNR=VALUES(LIFNR),
                    HERSTELLER=VALUES(HERSTELLER),
                    EMATNR=VALUES(EMATNR),
                    MATNR=VALUES(MATNR),
                    CHARG=VALUES(CHARG),
                    LAGORTCHRG=VALUES(LAGORTCHRG),
                    KDAUF=VALUES(KDAUF),
                    KDPOS=VALUES(KDPOS),
                    EBELN=VALUES(EBELN),
                    EBELP=VALUES(EBELP),
                    BLART=VALUES(BLART),
                    MJAHR=VALUES(MJAHR),
                    MBLNR=VALUES(MBLNR),
                    ZEILE=VALUES(ZEILE),
                    BUDAT=VALUES(BUDAT),
                    BWART=VALUES(BWART),
                    WERKVORG=VALUES(WERKVORG),
                    LAGORTVORG=VALUES(LAGORTVORG),
                    LS_KDPOS=VALUES(LS_KDPOS),
                    LS_VBELN=VALUES(LS_VBELN),
                    LS_POSNR=VALUES(LS_POSNR),
                    LS_ROUTE=VALUES(LS_ROUTE),
                    LS_KUNAG=VALUES(LS_KUNAG),
                    LS_VKORG=VALUES(LS_VKORG),
                    LS_KDMAT=VALUES(LS_KDMAT),
                    SPRACHE=VALUES(SPRACHE),
                    KTEXTMAT=VALUES(KTEXTMAT),
                    LOSMENGE=VALUES(LOSMENGE),
                    MENGENEINH=VALUES(MENGENEINH),
                    LMENGE01=VALUES(LMENGE01),
                    LMENGE04=VALUES(LMENGE04),
                    LMENGE07=VALUES(LMENGE07),
                    LMENGEZUB=VALUES(LMENGEZUB),
                    STAT34=VALUES(STAT34),
                    STAT35=VALUES(STAT35),
                    KTEXTLOS=VALUES(KTEXTLOS),
                    INSP_DOC_NUMBER=VALUES(INSP_DOC_NUMBER),
                    AUFPL=VALUES(AUFPL),
                    STATS=VALUES(STATS)
            """, values)

        conn_mysql.commit()
        cursor.close()
        conn_mysql.close()

        return jsonify({"message": f"{len(data)} inspection lot berhasil disimpan ke database."})

    except mysql.connector.Error as db_err:
        return jsonify({"error": f"MySQL error: {str(db_err)}"}), 500

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": f"Unexpected error: {str(e)}"}), 500