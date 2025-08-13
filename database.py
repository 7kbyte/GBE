import sqlite3
import click
from flask import current_app, g

def get_db():
    """获取数据库连接，如果不存在则创建并存储在 g 对象中"""
    if 'db' not in g:
        g.db = sqlite3.connect(
            current_app.config['DATABASE'],
            detect_types=sqlite3.PARSE_DECLTYPES
        )
        g.db.row_factory = sqlite3.Row # 使行数据可以像字典一样访问
    return g.db

def close_db(e=None):
    """关闭数据库连接"""
    db = g.pop('db', None)
    if db is not None:
        db.close()

def init_db():
    """初始化数据库，根据 schema.sql 创建表"""
    db = get_db()
    with current_app.open_resource('schema.sql') as f:
        db.executescript(f.read().decode('utf8'))

@click.command('init-db')
def init_db_command():
    """Flask CLI 命令：清除现有数据并创建新表"""
    init_db()
    click.echo('Initialized the database.')

def init_app(app):
    """注册数据库相关的函数到 Flask 应用"""
    app.teardown_appcontext(close_db) # 在请求结束后自动关闭数据库
    app.cli.add_command(init_db_command) # 添加命令行命令