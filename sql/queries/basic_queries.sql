-- SELECT * FROM user_credentials;
-- SELECT * FROM users;

-- SELECT * FROM  user_sessions


-- DELETE FROM token_blacklist;
-- DELETE FROM user_sessions;
-- DELETE FROM token_blacklist;
-- DELETE FROM user_sessions WHERE user_sessions.id = 'b81c5fe9-8148-48a2-b791-ffa0f2086175';
-- DELETE FROM password_reset_tokens;


SELECT * FROM user_sessions;

-- SELECT * FROM user_credentials;

-- SELECT * FROM users;

SELECT * FROM session_token_jtis;
SELECT * FROM token_blacklist; 

-- SELECT * FROM password_reset_tokens;

-- SELECT token_blacklist.jti FROM token_blacklist WHERE token_blacklist.jti IN ('b9f3a835-03b7-482e-9655-453f5e318b5c');  

-- SELECT count(name) FROM  users;