BEGIN;

DELETE FROM challenges;
INSERT INTO challenges (cid, team, t_start, t_stop) VALUES
  ('Attendance(expired)', 0, datetime('2018-01-01 00:00:00'), datetime('2018-01-01 14:00:00')),
  ('Attendance(solved)', 0, datetime('2018-01-05 00:00:00'), datetime('2018-01-05 14:00:00')),
  ('Attendance(active)', 0, datetime('now'), datetime('now','+1 day')),
  ('Attendance(future)', 0, datetime('2042-01-01 00:00:00'), datetime('2042-01-01 14:00:00'))
;

DELETE FROM users;
INSERT INTO users (uid, password) VALUES
  -- Username: userN
  -- Password: test
  ('user1', '$argon2i$v=19$m=512,t=2,p=2$xDeorlDXJFgubKyG+YJvHQ$MC1qibUX5Ah04ZFHVPsqNQ'),
  ('user2', '$argon2i$v=19$m=512,t=2,p=2$xDeorlDXJFgubKyG+YJvHQ$MC1qibUX5Ah04ZFHVPsqNQ'),
  ('user3', '$argon2i$v=19$m=512,t=2,p=2$xDeorlDXJFgubKyG+YJvHQ$MC1qibUX5Ah04ZFHVPsqNQ'),
  ('user4', '$argon2i$v=19$m=512,t=2,p=2$xDeorlDXJFgubKyG+YJvHQ$MC1qibUX5Ah04ZFHVPsqNQ')
;

DELETE FROM teams;
INSERT INTO teams (tid, uid) VALUES
  ('team1', 'user1'),
  ('team1', 'user2'),
  ('team2', 'user3')
;

DELETE FROM flags;
INSERT INTO flags (fid, cid, max_submissions) VALUES
  ('solved', 'Attendance(solved)', 999999)
;

DELETE FROM submissions;
INSERT INTO submissions (uid, fid) VALUES
  ('user1', 'solved')
;

COMMIT;
