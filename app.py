import os
import sqlite3
from flask import Flask, request, jsonify, g
from flask_cors import CORS # 用于处理跨域请求
from database import get_db, close_db, init_app

def create_app():
    app = Flask(__name__)
    CORS(app) # 启用 CORS，允许前端在不同端口访问后端

    # 应用配置
    app.config.from_mapping(
        SECRET_KEY='dev', # 在生产环境中应使用复杂随机密钥
        DATABASE=os.path.join(app.instance_path, 'game_rating.sqlite'), # 数据库文件路径
    )

    # 确保实例文件夹存在
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    init_app(app) # 初始化数据库相关功能

    @app.route('/')
    def index():
        return "Welcome to the Game Rating API!"

    # API 端点：获取所有游戏（仅ID和名称）
    @app.route('/api/games', methods=['GET'])
    def get_games():
        db = get_db()
        games = db.execute('SELECT id, name FROM games ORDER BY name ASC').fetchall()
        return jsonify([dict(game) for game in games])

    # API 端点：获取单个游戏详情
    @app.route('/api/games/<int:game_id>', methods=['GET'])
    def get_game(game_id):
        db = get_db()
        game = db.execute(
            'SELECT * FROM games WHERE id = ?', (game_id,)
        ).fetchone()
        if game is None:
            return jsonify({'error': 'Game not found'}), 404
        return jsonify(dict(game))

    # API 端点：创建新游戏
    @app.route('/api/games', methods=['POST'])
    def create_game():
        data = request.get_json()
        required_fields = ['name', 'art', 'music', 'story', 'playability', 'innovation', 'performance']
        if not all(field in data for field in required_fields):
            return jsonify({'error': '缺少必要字段'}), 400

        name = data['name']
        art = data['art']
        music = data['music']
        story = data['story']
        playability = data['playability']
        innovation = data['innovation']
        performance = data['performance']
        remarks = data.get('remarks', '')

        # 评分范围验证 (1-10)
        scores = [art, music, story, playability, innovation, performance]
        if not all(1 <= s <= 10 for s in scores):
            return jsonify({'error': '所有评分必须在 1 到 10 之间'}), 400
        
        # 备注长度验证 (不超过200字符)
        if len(remarks) > 200:
            return jsonify({'error': '备注不能超过 200 个字符'}), 400

        db = get_db()
        try:
            cursor = db.execute(
                'INSERT INTO games (name, art, music, story, playability, innovation, performance, remarks) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
                (name, art, music, story, playability, innovation, performance, remarks)
            )
            db.commit()
            return jsonify({'id': cursor.lastrowid, 'message': '游戏创建成功'}), 201
        except sqlite3.IntegrityError:
            return jsonify({'error': '游戏名称已存在'}), 409 # Conflict
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    # API 端点：更新游戏
    @app.route('/api/games/<int:game_id>', methods=['PUT'])
    def update_game(game_id):
        data = request.get_json()
        db = get_db()
        game = db.execute(
            'SELECT * FROM games WHERE id = ?', (game_id,)
        ).fetchone()
        if game is None:
            return jsonify({'error': '游戏未找到'}), 404

        update_fields = []
        update_values = []

        # 动态构建更新语句
        if 'name' in data:
            update_fields.append('name = ?')
            update_values.append(data['name'])
        
        score_fields = ['art', 'music', 'story', 'playability', 'innovation', 'performance']
        for field in score_fields:
            if field in data:
                score = data[field]
                if not (1 <= score <= 10):
                    return jsonify({'error': f'{field} 评分必须在 1 到 10 之间'}), 400
                update_fields.append(f'{field} = ?')
                update_values.append(score)
        
        if 'remarks' in data:
            remarks = data['remarks']
            if len(remarks) > 200:
                return jsonify({'error': '备注不能超过 200 个字符'}), 400
            update_fields.append('remarks = ?')
            update_values.append(remarks)

        if not update_fields:
            return jsonify({'error': '没有要更新的字段'}), 400

        update_query = f"UPDATE games SET {', '.join(update_fields)} WHERE id = ?"
        update_values.append(game_id) # WHERE 子句的参数

        try:
            db.execute(update_query, tuple(update_values))
            db.commit()
            return jsonify({'message': '游戏更新成功'})
        except sqlite3.IntegrityError:
            return jsonify({'error': '游戏名称已存在'}), 409
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    # API 端点：删除游戏
    @app.route('/api/games/<int:game_id>', methods=['DELETE'])
    def delete_game(game_id):
        db = get_db()
        cursor = db.execute('DELETE FROM games WHERE id = ?', (game_id,))
        db.commit()
        if cursor.rowcount == 0:
            return jsonify({'error': '游戏未找到'}), 404
        return jsonify({'message': '游戏删除成功'})

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True) # debug=True 可以在开发时自动重载和显示错误信息