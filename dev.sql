BEGIN;
DELETE FROM challenges;
INSERT INTO challenges (cid, team, t_start, t_stop) VALUES
  -- expired
  ('Attendance(01.01.2018)', 0, datetime('2018-01-01 00:00:00'), datetime('2018-01-01 14:00:00')),
  -- solved
  ('Attendance(05.01.2018)', 0, datetime('2018-01-05 00:00:00'), datetime('2018-01-05 14:00:00')),
  -- active
  ('Attendance(' || date('now') || ')', 0, datetime('now'), datetime('now','+1 day')),
  -- still invisible
  ('Attendance(01.01.2042)', 0, datetime('2042-01-01 00:00:00'), datetime('2042-01-01 14:00:00')),
  -- Other examples
  ('FormExample', 1, datetime('now'), datetime('now','+1 month')),
  ('FromFolder(../r8/misc/folder-example)', 1, datetime('now'), datetime('now','+1 month','start of day'))
;

DELETE FROM users;
INSERT INTO users (uid, password) VALUES
  -- Username: userN
  -- Password: test
  ('user1', '$argon2i$v=19$m=512,t=2,p=2$xDeorlDXJFgubKyG+YJvHQ$MC1qibUX5Ah04ZFHVPsqNQ'),
  ('user2', '$argon2i$v=19$m=512,t=2,p=2$xDeorlDXJFgubKyG+YJvHQ$MC1qibUX5Ah04ZFHVPsqNQ'),
  ('user3', '$argon2i$v=19$m=512,t=2,p=2$xDeorlDXJFgubKyG+YJvHQ$MC1qibUX5Ah04ZFHVPsqNQ')
;

DELETE FROM flags;
INSERT INTO flags (fid, cid, max_submissions) VALUES
  -- easy to memorize flags for testing.
  ('expired', 'Attendance(01.01.2018)', 999999),
  ('da', 'Attendance(' || date('now') || ')', 999999),
  ('limited', 'Attendance(' || date('now') || ')', 0),
  ('future', 'Attendance(01.01.2042)', 999999),
  ('solved', 'Attendance(05.01.2018)', 1)
;

DELETE FROM events;
INSERT INTO events (time, ip, type, data, cid, uid) VALUES
  ('2018-01-04 23:59:11', '127.0.0.1', 'get-challenges', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/64.0.3282.186 Safari/537.36', null, 'user1'),
  ('2018-01-04 23:59:25', '127.0.0.1', 'flag-submit', 'solved', 'Attendance(05.01.2018)', 'user1'),
  ('2018-01-04 23:59:32', '127.0.0.1', 'flag-err-solved', 'solved', 'Attendance(05.01.2018)', 'user1'),
  ('2018-01-04 23:59:59', '127.0.0.1', 'flag-err-unknown', 'a', null, 'user1');

DELETE FROM submissions;
INSERT INTO submissions (uid, fid) VALUES
  ('user1', 'solved')
;

DELETE FROM teams;
INSERT INTO teams (tid, uid) VALUES
  ('42', 'user1'),
  ('42', 'user2')
;
COMMIT;
