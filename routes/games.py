# routes/games.py
import sqlite3
from flask import Blueprint, request, jsonify, current_app
from database import get_db # 导入数据库连接函数
from routes.utils import get_or_create_tags # 导入辅助函数

# 创建一个蓝图实例
# 'games' 是蓝图的名称，__name__ 是当前模块的名称
# url_prefix='/games' 意味着所有定义在此蓝图中的路由都会自动加上 /games 前缀
games_bp = Blueprint('games', __name__, url_prefix='/games')

# API 端点：获取所有游戏 (支持搜索、排序、分页)
# GET /games?search=<keyword>&sort_by=<rating_field>&order=<asc/desc>&page=<num>&per_page=<num>
@games_bp.route('/', methods=['GET']) # 注意这里是 '/'，因为前缀已经是 /games
def get_all_games():
    db = get_db()
    search_query = request.args.get('search', '')
    sort_by = request.args.get('sort_by', 'id') # 默认按ID排序
    order = request.args.get('order', 'asc').upper() # 默认升序

    # 分页参数
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    offset = (page - 1) * per_page

    # 验证排序字段
    allowed_sort_fields = [
        'id', 'name', 'release_year', 'art_rating', 'music_rating',
        'story_rating', 'playability_rating', 'innovation_rating',
        'performance_rating', 'my_overall_score', 'created_at', 'updated_at',
        'random' # 新增随机排序选项
    ]
    if sort_by not in allowed_sort_fields:
        return jsonify({"error": f"Invalid sort_by field. Allowed: {', '.join(allowed_sort_fields)}"}), 400

    # 验证排序顺序 (仅当不是随机排序时才验证)
    if sort_by != 'random' and order not in ['ASC', 'DESC']:
        return jsonify({"error": "Invalid order. Must be 'asc' or 'desc'"}), 400

    # 构建查询条件和参数
    conditions = []
    query_params = []

    if search_query:
        search_pattern = f'%{search_query}%'
        # 搜索游戏名称、评价、开发者、发行商、平台，以及关联的标签名称
        conditions.append("""
            (g.name LIKE ? OR g.review_text LIKE ? OR g.developer LIKE ? OR g.publisher LIKE ? OR g.platform LIKE ?
            OR EXISTS (SELECT 1 FROM game_tags gt_sub JOIN tags t_sub ON gt_sub.tag_id = t_sub.id WHERE gt_sub.game_id = g.id AND t_sub.name LIKE ?))
        """)
        query_params.extend([search_pattern] * 5) # 对应5个游戏字段的模糊匹配
        query_params.append(search_pattern) # 对应标签名称的模糊匹配

    where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""

    # 获取总游戏数（用于分页）
    # 注意：对于随机排序，总数获取不受影响，因为随机性只影响 ORDER BY
    count_sql = f"SELECT COUNT(DISTINCT g.id) FROM games g {where_clause}"
    total_games = db.execute(count_sql, tuple(query_params)).fetchone()[0]

    # 构建 ORDER BY 子句
    order_by_clause = ""
    if sort_by == 'random':
        order_by_clause = "ORDER BY RANDOM()" # SQLite 的随机排序函数
    else:
        order_by_clause = f"ORDER BY g.{sort_by} {order}"

    # 主查询：获取游戏数据及关联标签
    sql = f"""
        SELECT
            g.*,
            GROUP_CONCAT(t.name) AS tags
        FROM
            games g
        LEFT JOIN
            game_tags gt ON g.id = gt.game_id
        LEFT JOIN
            tags t ON gt.tag_id = t.id
        {where_clause}
        GROUP BY
            g.id
        {order_by_clause}
        LIMIT ? OFFSET ?
    """
    query_params.extend([per_page, offset]) # 添加分页参数

    games_cursor = db.execute(sql, tuple(query_params))
    games = games_cursor.fetchall()

    games_list = []
    for game in games:
        game_dict = dict(game)
        game_dict['tags'] = game_dict['tags'].split(',') if game_dict['tags'] else []
        games_list.append(game_dict)

    return jsonify({
        "games": games_list,
        "total_games": total_games,
        "page": page,
        "per_page": per_page,
        "total_pages": (total_games + per_page - 1) // per_page
    })

# API 端点：获取单个游戏详情
# GET /games/<game_id>
@games_bp.route('/<int:game_id>', methods=['GET'])
def get_game_detail(game_id):
    db = get_db()
    cursor = db.execute("""
        SELECT
            g.*,
            GROUP_CONCAT(t.name) AS tags
        FROM
            games g
        LEFT JOIN
            game_tags gt ON g.id = gt.game_id
        LEFT JOIN
            tags t ON gt.tag_id = t.id
        WHERE
            g.id = ?
        GROUP BY
            g.id
    """, (game_id,))
    game = cursor.fetchone()

    if game is None:
        return jsonify({"error": "Game not found"}), 404

    game_dict = dict(game)
    game_dict['tags'] = game_dict['tags'].split(',') if game_dict['tags'] else []
    return jsonify(game_dict)

# API 端点：创建新游戏
# POST /games
@games_bp.route('/', methods=['POST'])
def create_game():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Request must be JSON"}), 400
    
    # 验证必需字段
    if 'name' not in data:
        return jsonify({"error": f"Missing required field: name"}), 400
    required_fields = ['art_rating', 'music_rating', 'story_rating',
                       'playability_rating', 'innovation_rating', 'performance_rating']
    for field in required_fields:
        if field not in data:
            return jsonify({"error": f"Missing required field: {field}"}), 400
        try:
            data[field] = float(data[field])
            if not (0.0 <= data[field] <= 10.0):
                return jsonify({"error": f"{field} must be between 0.0 and 10.0"}), 400
        except (ValueError, TypeError):
            return jsonify({"error": f"{field} must be a valid number"}), 400

    db = get_db()
    try:
        cursor = db.execute("""
            INSERT INTO games (
                name, image_url, release_year, developer, publisher, platform,
                art_rating, music_rating, story_rating, playability_rating,
                innovation_rating, performance_rating, review_text,
                my_overall_score, is_completed, play_time_hours
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data['name'],
            data.get('image_url'),
            data.get('release_year'),
            data.get('developer'),
            data.get('publisher'),
            data.get('platform'),
            data['art_rating'],
            data['music_rating'],
            data['story_rating'],
            data['playability_rating'],
            data['innovation_rating'],
            data['performance_rating'],
            data.get('review_text'),
            data.get('my_overall_score'),
            data.get('is_completed', False),
            data.get('play_time_hours')
        ))
        # print(f"DEBUG: Type of 'cursor' object: {type(cursor)}") 
        game_id = cursor.lastrowid

        if 'tags' in data and isinstance(data['tags'], list):
            tag_ids = get_or_create_tags(db, data['tags'])
            for tag_id in tag_ids:
                db.execute("INSERT OR IGNORE INTO game_tags (game_id, tag_id) VALUES (?, ?)", (game_id, tag_id))

        db.commit()
        return jsonify({"message": "Game created successfully", "game_id": game_id}), 201
    except sqlite3.IntegrityError as e:
        db.rollback()
        if "UNIQUE constraint failed: games.name" in str(e):
            return jsonify({"error": "Game with this name already exists"}), 409
        return jsonify({"error": f"Database error: {str(e)}"}), 500
    except Exception as e:
        db.rollback()
        return jsonify({"error": f"An unexpected error occurred: {str(e)}"}), 500

# API 端点：更新游戏
# PUT /games/<game_id>
@games_bp.route('/<int:game_id>', methods=['PUT'])
def update_game(game_id):
    data = request.get_json()
    if not data:
        return jsonify({"error": "Request must be JSON"}), 400

    db = get_db()
    cursor = db.execute("SELECT id FROM games WHERE id = ?", (game_id,))
    if cursor.fetchone() is None:
        return jsonify({"error": "Game not found"}), 404

    try:
        update_fields = []
        update_values = []
        
        updatable_fields = [
            'name', 'image_url', 'release_year', 'developer', 'publisher', 'platform',
            'art_rating', 'music_rating', 'story_rating', 'playability_rating',
            'innovation_rating', 'performance_rating', 'review_text',
            'my_overall_score', 'is_completed', 'play_time_hours'
        ]

        for field in updatable_fields:
            if field in data:
                if '_rating' in field:
                    try:
                        data[field] = float(data[field])
                        if not (0.0 <= data[field] <= 10.0):
                            return jsonify({"error": f"{field} must be between 0.0 and 10.0"}), 400
                    except (ValueError, TypeError):
                        return jsonify({"error": f"{field} must be a valid number"}), 400
                
                update_fields.append(f"{field} = ?")
                update_values.append(data[field])
        
        if not update_fields and 'tags' not in data:
            return jsonify({"message": "No fields to update"}), 200

        update_fields.append("updated_at = CURRENT_TIMESTAMP")
        update_sql = f"UPDATE games SET {', '.join(update_fields)} WHERE id = ?"
        update_values.append(game_id)

        db.execute(update_sql, tuple(update_values))

        if 'tags' in data and isinstance(data['tags'], list):
            db.execute("DELETE FROM game_tags WHERE game_id = ?", (game_id,))
            
            tag_ids = get_or_create_tags(db, data['tags'])
            for tag_id in tag_ids:
                db.execute("INSERT OR IGNORE INTO game_tags (game_id, tag_id) VALUES (?, ?)", (game_id, tag_id))

        db.commit()
        return jsonify({"message": "Game updated successfully"}), 200
    except sqlite3.IntegrityError as e:
        db.rollback()
        if "UNIQUE constraint failed: games.name" in str(e):
            return jsonify({"error": "Game with this name already exists"}), 409
        return jsonify({"error": f"Database error: {str(e)}"}), 500
    except Exception as e:
        db.rollback()
        return jsonify({"error": f"An unexpected error occurred: {str(e)}"}), 500

# API 端点：删除游戏
# DELETE /games/<game_id>
@games_bp.route('/<int:game_id>', methods=['DELETE'])
def delete_game(game_id):
    db = get_db()
    try:
        cursor = db.execute("DELETE FROM games WHERE id = ?", (game_id,))
        db.commit()
        if cursor.rowcount == 0:
            return jsonify({"error": "Game not found"}), 404
        return jsonify({"message": "Game deleted successfully"}), 200
    except Exception as e:
        db.rollback()
        return jsonify({"error": f"An unexpected error occurred: {str(e)}"}), 500

# API 端点：添加游戏标签 (为特定游戏添加一个或多个标签)
# POST /games/<game_id>/tags
@games_bp.route('/<int:game_id>/tags', methods=['POST'])
def add_game_tags(game_id):
    data = request.get_json()
    if not data or 'tags' not in data or not isinstance(data['tags'], list):
        return jsonify({"error": "Request must be JSON with a 'tags' list"}), 400

    db = get_db()
    cursor = db.execute("SELECT id FROM games WHERE id = ?", (game_id,))
    if cursor.fetchone() is None:
        return jsonify({"error": "Game not found"}), 404

    try:
        tag_ids = get_or_create_tags(db, data['tags'])
        added_count = 0
        for tag_id in tag_ids:
            cursor = db.execute("INSERT OR IGNORE INTO game_tags (game_id, tag_id) VALUES (?, ?)", (game_id, tag_id))
            if cursor.rowcount > 0:
                added_count += 1
        db.commit()
        return jsonify({"message": f"Successfully added {added_count} new tags to game {game_id}"}), 200
    except Exception as e:
        db.rollback()
        return jsonify({"error": f"An unexpected error occurred: {str(e)}"}), 500

# API 端点：删除游戏标签 (删除某个游戏的某个特定标签)
# DELETE /games/<game_id>/tags/<tag_id>
@games_bp.route('/<int:game_id>/tags/<int:tag_id>', methods=['DELETE'])
def delete_game_tag(game_id, tag_id):
    db = get_db()
    try:
        cursor = db.execute("DELETE FROM game_tags WHERE game_id = ? AND tag_id = ?", (game_id, tag_id))
        db.commit()
        if cursor.rowcount == 0:
            return jsonify({"error": "Game-tag relationship not found"}), 404
        return jsonify({"message": "Game tag deleted successfully"}), 200
    except Exception as e:
        db.rollback()
        return jsonify({"error": f"An unexpected error occurred: {str(e)}"}), 500