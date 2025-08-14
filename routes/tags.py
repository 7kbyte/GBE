# routes/tags.py
import sqlite3
from flask import Blueprint, request, jsonify, current_app
from database import get_db # 导入数据库连接函数

# 创建一个蓝图实例
# url_prefix='/tags' 意味着所有定义在此蓝图中的路由都会自动加上 /tags 前缀
tags_bp = Blueprint('tags', __name__, url_prefix='/tags')

# API 端点：标签查询 (获取所有可用的标签)
# GET /tags
@tags_bp.route('/', methods=['GET']) # 注意这里是 '/'
def get_all_tags():
    db = get_db()
    tags_cursor = db.execute("SELECT id, name FROM tags ORDER BY name ASC")
    tags = [dict(row) for row in tags_cursor.fetchall()]
    return jsonify({"tags": tags})

# API 端点：删除一个标签 (此操作将从所有游戏中移除该标签)
# DELETE /tags/<tag_id>
@tags_bp.route('/<int:tag_id>', methods=['DELETE'])
def delete_tag(tag_id):
    db = get_db()
    try:
        cursor = db.execute("DELETE FROM tags WHERE id = ?", (tag_id,))
        db.commit()
        if cursor.rowcount == 0:
            return jsonify({"error": "Tag not found"}), 404
        return jsonify({"message": "Tag deleted successfully"}), 200
    except Exception as e:
        db.rollback()
        return jsonify({"error": f"An unexpected error occurred: {str(e)}"}), 500