BEGIN;

-- Configure which challenge instances should be displayed to users at which point in time.
-- Note that times are generally UTC.
-- You can pass a single string argument to challenges by appending it in parentheses.
DELETE FROM challenges;
INSERT INTO challenges (cid, team, t_start, t_stop) VALUES
  -- expired
  ('Basic(Example Challenge (expired))', 0, datetime('2000-01-01 00:00:00'), datetime('2011-01-01 11:11:00+01:00')),
  -- solved
  ('Basic(Example Challenge (solved))', 0, datetime('now'), datetime('now','+1 month')),
  -- active
  ('Basic(Example Challenge (active))', 0, datetime('now'), datetime('now','+1 month')),
  -- still invisible
  ('Basic(Example Challenge (appears in the future))', 0, datetime('2042-01-01 00:00:00'), datetime('2042-01-01 14:00:00')),
  -- Other examples
  ('TcpServer', 1, datetime('now'), datetime('now','+1 month')),
  ('WebServer', 1, datetime('now'), datetime('now','+1 month')),
  ('FormExample', 1, datetime('now'), datetime('now','+1 month')),
  ('DockerHelloWorld', 1, datetime('now'), datetime('now','+1 month')),
  ('FromFolder(../r8/misc/folder-example)', 1, datetime('now'), datetime('now','+1 month','start of day'))
;

-- Configure all user accounts. See `r8 password --help` for password generation.
DELETE FROM users;
INSERT INTO users (uid, password) VALUES
  -- Username: userN
  -- Password: test
  ('user1', '$argon2i$v=19$m=512,t=2,p=2$xDeorlDXJFgubKyG+YJvHQ$MC1qibUX5Ah04ZFHVPsqNQ'),
  ('user2', '$argon2i$v=19$m=512,t=2,p=2$xDeorlDXJFgubKyG+YJvHQ$MC1qibUX5Ah04ZFHVPsqNQ'),
  ('user3', '$argon2i$v=19$m=512,t=2,p=2$xDeorlDXJFgubKyG+YJvHQ$MC1qibUX5Ah04ZFHVPsqNQ')
;

-- Configure all teams. For challenges with team=1,
-- a single submission will mark challenges as solved by all team members.
DELETE FROM teams;
INSERT INTO teams (tid, uid) VALUES
  ('42', 'user1'),
  ('42', 'user2')
;

--
--
-- The SQL statements below only serve to illustrate the r8 UI.
-- In a production deployment, we would COMMIT; here and be done.
--
--

DELETE FROM flags;
INSERT INTO flags (fid, cid, max_submissions) VALUES
  -- easy to memorize flags for testing.
  ('expired', 'Basic(Example Challenge (expired))', 999999),
  ('active', 'Basic(Example Challenge (active))', 999999),
  ('limited', 'Basic(Example Challenge (active))', 0),
  ('future', 'Basic(Example Challenge (appears in the future))', 999999),
  ('solved', 'Basic(Example Challenge (solved))', 1)
;

DELETE FROM events;
INSERT INTO events (time, ip, type, data, cid, uid) VALUES
  (datetime('now','-60 seconds'), '127.0.0.1', 'get-challenges', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/64.0.3282.186 Safari/537.36', null, 'user1'),
  (datetime('now','-40 seconds'), '127.0.0.1', 'flag-submit', 'solved', 'Basic(Example Challenge (solved))', 'user1'),
  (datetime('now','-37 seconds'), '127.0.0.1', 'flag-err-solved', 'solved', 'Basic(Example Challenge (solved))', 'user1'),
  (datetime('now','-21 seconds'), '127.0.0.1', 'flag-err-unknown', 'a', null, 'user1');

DELETE FROM submissions;
INSERT INTO submissions (uid, fid) VALUES
  ('user1', 'solved')
;

COMMIT;
