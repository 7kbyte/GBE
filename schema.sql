-- 删除现有表（如果存在），以便重新创建
DROP TABLE IF EXISTS game_tags;
DROP TABLE IF EXISTS tags;
DROP TABLE IF EXISTS games;

-- 1. games 表：存储游戏的基本信息、评分和评价
CREATE TABLE games (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE, -- 游戏名称，不能为空且唯一
    image_url TEXT,            -- 游戏封面图片URL（存储路径或外部链接），可以为空
    release_year INTEGER,      -- 发行年份，可用于排序和筛选
    developer TEXT,            -- 开发者，可用于搜索
    publisher TEXT,            -- 发行商，可用于搜索
    platform TEXT,             -- 平台 (例如: "PC", "PS5", "Switch", "PC, PS5"等，简单起见用文本存储)

    -- 6项评分 (现在是 REAL 类型，0.0-10.0)
    art_rating REAL NOT NULL CHECK (art_rating >= 0.0 AND art_rating <= 10.0),
    music_rating REAL NOT NULL CHECK (music_rating >= 0.0 AND music_rating <= 10.0),
    story_rating REAL NOT NULL CHECK (story_rating >= 0.0 AND story_rating <= 10.0),
    playability_rating REAL NOT NULL CHECK (playability_rating >= 0.0 AND playability_rating <= 10.0),
    innovation_rating REAL NOT NULL CHECK (innovation_rating >= 0.0 AND innovation_rating <= 10.0),
    performance_rating REAL NOT NULL CHECK (performance_rating >= 0.0 AND performance_rating <= 10.0),

    review_text TEXT,          -- 您的文字评价，可以为空
    my_overall_score REAL CHECK (my_overall_score >= 0.0 AND my_overall_score <= 10.0), -- 可选：您的综合评分
    is_completed BOOLEAN DEFAULT FALSE, -- 是否已通关，默认为否 (在SQLite中BOOLEAN通常存储为0或1)
    play_time_hours INTEGER,   -- 游玩时长（小时），可以为空

    created_at DATETIME DEFAULT CURRENT_TIMESTAMP, -- 记录创建时间
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP   -- 记录最后更新时间
);

-- 2. tags 表：存储所有独特的标签
CREATE TABLE tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE -- 标签名称，不能为空且唯一 (例如: "RPG", "动作", "独立游戏", "科幻")
);

-- 3. game_tags 表：关联游戏和标签 (多对多关系)
CREATE TABLE game_tags (
    game_id INTEGER NOT NULL, -- 关联到 games 表的 id
    tag_id INTEGER NOT NULL,  -- 关联到 tags 表的 id
    PRIMARY KEY (game_id, tag_id), -- 复合主键，确保一个游戏-标签组合的唯一性
    FOREIGN KEY (game_id) REFERENCES games(id) ON DELETE CASCADE, -- 当游戏被删除时，自动删除其所有标签关联
    FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE    -- 当标签被删除时，自动删除所有关联到该标签的游戏记录
);