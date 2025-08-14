import os
import sqlite3
from flask import Flask, request, jsonify, g
from flask_cors import CORS
from database import get_db, close_db, init_app

# 导入蓝图
from routes.games import games_bp
from routes.tags import tags_bp

def create_app():
    app = Flask(__name__)
    CORS(app)

    app.config.from_mapping(
        SECRET_KEY='dev',
        DATABASE=os.path.join(app.instance_path, 'game_rating.sqlite'),
    )

    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    init_app(app)

    # 注册蓝图
    app.register_blueprint(games_bp)
    app.register_blueprint(tags_bp)

    @app.route('/')
    def index():
        return "Welcome to the Game Rating API!"

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)