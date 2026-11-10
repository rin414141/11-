-- 補助金マスタのサンプル（初回起動時に1回だけ入る）
-- date('now', '+4 day') は「今日から4日後」の日付
INSERT INTO subsidy (name, amount, difficulty, deadline, official_url, category, target_area, single_parent_only, child_required, income_max, updated_at) VALUES
('児童手当',               '月1万円〜／1人',        'easy',   NULL,                     'https://www.cfa.go.jp/', '子育て',       '00', 0, 1, NULL, datetime('now')),
('出産育児一時金',         '1児につき50万円',       'easy',   NULL,                     'https://www.mhlw.go.jp/', '子育て',      '00', 0, 0, NULL, datetime('now')),
('就学援助（市区町村）',   '学用品費・給食費など',  'normal', date('now', '+4 day'),    'https://www.mext.go.jp/', '教育',        '00', 0, 1, 2,    datetime('now')),
('高等学校等就学支援金',   '年11万8,800円〜',       'normal', date('now', '+20 day'),   'https://www.mext.go.jp/', '教育',        '00', 0, 1, 3,    datetime('now')),
('児童扶養手当',           '月最大4万6,690円',      'normal', NULL,                     'https://www.cfa.go.jp/', 'ひとり親支援', '00', 1, 1, 2,    datetime('now')),
('育児休業給付金',         '休業前の賃金の67%',     'normal', NULL,                     'https://www.mhlw.go.jp/', '仕事',        '00', 0, 0, NULL, datetime('now')),
('018サポート（東京都）',  '月5,000円／1人',        'easy',   NULL,                     'https://www.fukushi.metro.tokyo.lg.jp/', 'お金', '13', 0, 1, NULL, datetime('now'));
