
from flask import Blueprint, request, jsonify
import mysql.connector
import json
from app.utils.helpers import save_base64_image
from config import db_config

inspections_bp = Blueprint('inspections_bp', __name__)

@inspections_bp.route('/submit-to-sql', methods=['POST'])
def submit_inspection():
    try:
        inspection = request.json
        data = {
            'prueflos': inspection['prueflos'],
            'charg': inspection['charg'],
            'inspection_date': inspection['inspection_date'],
            'unit': inspection['unit'],
            'location': inspection['location'],
            'ktexmat': inspection['ktexmat'],
            'dispo': inspection['dispo'],
            'mengeneinh': inspection['entry_uom'],
            'lagortchrg': inspection['stge_loc'],
            'kdpos': inspection['kdpos'],
            'kdauf': inspection['kdauf'],
            'nik_qc': inspection['nik_qc'],
            'cause_effect': inspection['cause_effect'],
            'correction': inspection['correction'],
            'aql_critical_found': int(inspection['aql_critical_found']),
            'aql_critical_allowed': int(inspection['aql_critical_allowed']),
            'aql_major_found': int(inspection['aql_major_found']),
            'aql_major_allowed': int(inspection['aql_major_allowed']),
            'aql_minor_found': int(inspection['aql_minor_found']),
            'aql_minor_allowed': int(inspection['aql_minor_allowed']),
            'inspection_items': json.dumps(inspection.get('inspection_items', [])),
            'img_top_view' : inspection.get('img_top_view'),
            'img_bottom_view' : inspection.get('img_bottom_view'),
            'img_front_view' : inspection.get('img_front_view'),
            'img_back_view' : inspection.get('img_back_view'),
            'username' : inspection.get('username')
        }
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        sql = f"""
            INSERT INTO quality_inspections (
                {', '.join(data.keys())}
            ) VALUES (
                {', '.join(['%s'] * len(data))}
            )
        """
        cursor.execute(sql, list(data.values()))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"message": "Data inspeksi berhasil disimpan", "status" : "BERHASIL"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
