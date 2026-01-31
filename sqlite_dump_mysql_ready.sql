SET FOREIGN_KEY_CHECKS=0;
DROP TABLE IF EXISTS jogador;
CREATE TABLE jogador (
	id INT NOT NULL, 
	nome VARCHAR(100) NOT NULL, 
	apelido VARCHAR(50), 
	posicao VARCHAR(50), 
	nivel VARCHAR(20), 
	telefone VARCHAR(20), 
	mensalista TINYINT(1), 
	mensalidade_paga TINYINT(1), 
	data_inicio_mensalidade DATE, 
	data_fim_mensalidade DATE, 
	capitao TINYINT(1), 
	ordem_capitao INT, 
	ativo TINYINT(1), 
	data_cadastro DATETIME, 
	rating INT, 
	foto_perfil VARCHAR(200), 
	altura VARCHAR(10), 
	data_nascimento DATE, 
	cidade VARCHAR(100), 
	PRIMARY KEY (id)
);
INSERT INTO jogador VALUES(1,'Samuel','','levantador','intermediario','(38) 98849-3735',1,1,'2026-01-08','2026-02-05',1,2,1,'2026-01-29 04:30:18.344517',1000,'/static/uploads/jogador_1_1769687031.2617.png','1,84','1999-03-30','Montes Claros');
INSERT INTO jogador VALUES(2,'Daniel','Daniel','levantador','iniciante','',1,1,'2026-01-08','2026-02-05',1,1,1,'2026-01-29 13:50:36.838988',1000,NULL,'','1997-12-19','');
INSERT INTO jogador VALUES(3,'Natan','Natanzinho','levantador','avancado','(38) 4002-8922',1,1,'2026-01-08','2026-02-05',0,0,1,'2026-01-29 13:58:22.087249',1000,'/static/uploads/jogador_3_1769703543.293668.png','2,00','1994-07-30','montes claros');
INSERT INTO jogador VALUES(4,'Caio lima','','','iniciante','',1,1,'2026-01-08','2026-02-05',0,0,1,'2026-01-29 13:59:39.987386',1000,'/static/uploads/jogador_4_1769695318.410227.jpg','','2001-01-29','');
INSERT INTO jogador VALUES(5,'Carlos','Carlin','','intermediario','',1,1,'2026-01-08','2026-02-05',0,0,1,'2026-01-29 14:00:10.964584',1000,'/static/uploads/jogador_5_20260129_140011_264196.jpg','','1999-05-30','');
INSERT INTO jogador VALUES(6,'Livia','Livia','libero','iniciante','',1,1,'2026-01-08','2026-02-05',0,0,1,'2026-01-29 14:02:00.801018',1000,'/static/uploads/jogador_6_1769695353.390965.jpg',NULL,'2005-04-12','Montes Claros');
INSERT INTO jogador VALUES(7,'João Resende','Resende','nao_informado','iniciante','(55) 31992-253077',0,0,NULL,NULL,0,0,1,'2026-01-29 14:06:18.658113',1000,'/static/uploads/jogador_7_1769695620.992256.jpg','1,79','2004-06-06','Montes Claros');
INSERT INTO jogador VALUES(8,'Dayvid Gabriel','LittleR','ponteiro','intermediario','(31) 98224-5815',0,0,NULL,NULL,0,0,1,'2026-01-29 14:07:49.816602',1000,'/static/uploads/jogador_8_1769695774.166039.jpg','1,78','2008-06-02','Montes Claros');
INSERT INTO jogador VALUES(9,'Ludmilla','','nao_informado','iniciante','(38) 98846-2602',1,1,'2026-01-08','2026-02-05',0,0,1,'2026-01-29 14:09:54.064187',1000,NULL,NULL,NULL,'');
INSERT INTO jogador VALUES(10,'Polliane','Polliane','','intermediario','',1,1,'2026-01-08','2026-02-05',1,4,1,'2026-01-29 14:10:13.605152',1000,NULL,'',NULL,'');
INSERT INTO jogador VALUES(11,'Filipe','','','intermediario','',1,1,'2026-01-08','2026-02-05',0,0,1,'2026-01-29 14:12:19.586546',1000,NULL,'',NULL,'');
INSERT INTO jogador VALUES(12,'Carlinhos Roberto','Carlinhos Roberto','','iniciante','(38) 99196-7194',1,1,'2026-01-08','2026-02-05',0,0,1,'2026-01-29 14:16:07.531102',1000,'/static/uploads/jogador_12_1769696199.858416.jpg','1,79','1980-10-03','Montes Claros');
INSERT INTO jogador VALUES(13,'Mariana','Nana','','intermediario','',1,1,'2026-01-08','2026-02-05',1,3,1,'2026-01-29 14:18:42.531899',1000,'/static/uploads/jogador_13_1769696375.562296.jpg','','2005-09-02','');
INSERT INTO jogador VALUES(14,'Ana Luiza','Ana','','iniciante','',1,1,'2026-01-08','2026-02-05',0,0,1,'2026-01-29 14:22:12.184719',1000,NULL,NULL,'2001-01-29','');
INSERT INTO jogador VALUES(15,'João Guilherme','Gui','nao_informado','iniciante','(55) 38991-785524',1,1,'2026-01-08','2026-02-05',0,0,1,'2026-01-29 14:26:20.344617',1000,'/static/uploads/jogador_15_20260129_142620_408174.jpg','1,60','1998-10-25','Montes Claros');
INSERT INTO jogador VALUES(16,'Fernanda','','central','iniciante','',1,1,'2026-01-08','2026-02-05',0,0,1,'2026-01-29 14:31:24.099105',1000,'/static/uploads/jogador_16_20260129_143124_162094.jpeg',NULL,'1997-03-10','');
INSERT INTO jogador VALUES(17,'Max Araújo','Maxi','central','intermediario','(38) 99970-3897',0,0,NULL,NULL,0,0,1,'2026-01-29 15:32:31.137574',1000,NULL,'1,86','2000-01-27','Montes claros');
INSERT INTO jogador VALUES(18,'Débora','Debs','','intermediario','',1,1,'2026-01-08','2026-02-05',0,0,1,'2026-01-29 16:38:08.340429',1000,'/static/uploads/jogador_18_20260129_163808_404930.jpeg',NULL,'1998-09-14','');
INSERT INTO jogador VALUES(19,'Jefferson','Jefferson','','iniciante','(38) 99817-6759',1,1,'2026-01-08','2026-02-05',0,0,1,'2026-01-29 18:25:11.444741',1000,'/static/uploads/jogador_19_1769711144.405303.png','1,00','2006-01-02','tokyo');
INSERT INTO jogador VALUES(20,'Lucas','Lulu','','intermediario','',1,1,'2026-01-08','2026-02-05',0,0,1,'2026-01-29 18:30:50.013205',1000,NULL,NULL,'2001-01-29','');
INSERT INTO jogador VALUES(21,'Marley','Monaliso','nao_informado','intermediario','',1,1,'2026-01-08','2026-02-05',0,0,1,'2026-01-29 18:31:23.085447',1000,NULL,NULL,'2001-01-29','');
INSERT INTO jogador VALUES(22,'Monalisa','','nao_informado','intermediario','',1,1,'2026-01-08','2026-02-05',0,0,1,'2026-01-29 18:32:07.504952',1000,NULL,NULL,'2001-01-29','');
INSERT INTO jogador VALUES(23,'Jefferson Fernandes','Jefferson','','intermediario','(38) 99136-2466',1,1,'2026-01-08','2026-02-05',0,0,1,'2026-01-29 18:33:50.358976',1000,NULL,'1,67','1991-03-16','Montes Claros');
INSERT INTO jogador VALUES(24,'Rafael','Hudson','nao_informado','intermediario','',1,1,'2026-01-08','2026-02-05',0,0,1,'2026-01-29 18:34:31.993202',1000,NULL,NULL,'2001-01-29','');
INSERT INTO jogador VALUES(25,'Raissa','','','intermediario','',1,1,'2026-01-08','2026-02-05',0,0,1,'2026-01-31 14:12:27.478716',1000,NULL,NULL,'2001-01-31','');
INSERT INTO jogador VALUES(26,'Brenda','Gabrielle','','intermediario','',1,1,'2026-01-08','2026-02-05',0,0,1,'2026-01-31 14:13:56.985821',1000,NULL,'','2001-01-31','');
DROP TABLE IF EXISTS semana;
CREATE TABLE semana (
	id INT NOT NULL, 
	data DATE NOT NULL, 
	descricao VARCHAR(200), 
	lista_aberta TINYINT(1), 
	lista_encerrada TINYINT(1), 
	draft_em_andamento TINYINT(1), 
	draft_finalizado TINYINT(1), 
	max_times INT, 
	max_jogadores_por_time INT, 
	tempo_escolha INT, 
	modo_draft VARCHAR(20), 
	created_at DATETIME, 
	encerrada_em DATETIME, 
	PRIMARY KEY (id), 
	UNIQUE (data)
);
INSERT INTO semana VALUES(1,'2026-01-28','Jogo de Vôlei - 28/01/2026',1,0,0,0,4,6,0,'linear','2026-01-29 02:36:04.744901',NULL);
INSERT INTO semana VALUES(3,'2026-01-10','Teste',1,0,0,0,2,6,30,'snake','2026-01-29 03:00:54.178622',NULL);
INSERT INTO semana VALUES(4,'2026-02-05','Jogo de Vôlei - 05/02/2026',1,0,0,0,4,6,0,'linear','2026-01-29 03:27:28.372478',NULL);
INSERT INTO semana VALUES(5,'2026-01-29','Jogo de Vôlei - 29/01/2026',0,1,0,1,4,6,0,'linear','2026-01-29 03:27:37.210966',NULL);
INSERT INTO semana VALUES(6,'2026-01-30','teste',1,0,0,0,2,6,30,'snake','2026-01-31 02:58:05.035389',NULL);
DROP TABLE IF EXISTS configuracao_semana;
CREATE TABLE configuracao_semana (
	id INT NOT NULL, 
	semana_id INT NOT NULL, 
	max_times INT, 
	max_jogadores_por_time INT, 
	tempo_por_escolha INT, 
	modo_draft VARCHAR(20), 
	created_at DATETIME, 
	PRIMARY KEY (id), 
	UNIQUE (semana_id), 
	FOREIGN KEY(semana_id) REFERENCES semana (id)
);
DROP TABLE IF EXISTS pix_info;
CREATE TABLE pix_info (
	id INT NOT NULL, 
	chave_pix VARCHAR(100) NOT NULL, 
	tipo_chave VARCHAR(50), 
	nome_recebedor VARCHAR(100) NOT NULL, 
	cidade_recebedor VARCHAR(100), 
	descricao VARCHAR(200), 
	ativo TINYINT(1), 
	created_at DATETIME, 
	para_todas_semanas TINYINT(1), 
	semana_id INT, 
	PRIMARY KEY (id), 
	FOREIGN KEY(semana_id) REFERENCES semana (id)
);
INSERT INTO pix_info VALUES(1,'11141504600','cpf','Daniel Sanzio','Montes Claros','R$7 Convidados Janeiro - R$22 Mensalistas Janeiro',1,'2026-01-29 04:48:30.384081',1,NULL);
DROP TABLE IF EXISTS recado;
CREATE TABLE recado (
	id INT NOT NULL, 
	titulo VARCHAR(200) NOT NULL, 
	conteudo TEXT NOT NULL, 
	autor VARCHAR(100), 
	importante TINYINT(1), 
	data_publicacao DATETIME, 
	data_expiracao DATE, 
	ativo TINYINT(1), 
	para_todas_semanas TINYINT(1), 
	semana_id INT, 
	PRIMARY KEY (id), 
	FOREIGN KEY(semana_id) REFERENCES semana (id)
);
INSERT INTO recado VALUES(1,'Quintas feiras','19 as 22h - Beach Center Unidade 1 - Todos os santos','admin',0,'2026-01-29 04:52:02.743351',NULL,1,1,NULL);
INSERT INTO recado VALUES(2,'Pagar','Vamos pagar ae convidados','admin',1,'2026-01-29 04:55:18.053979',NULL,1,1,NULL);
DROP TABLE IF EXISTS user;
CREATE TABLE user (
	id INT NOT NULL, 
	username VARCHAR(80) NOT NULL, 
	password VARCHAR(200) NOT NULL, 
	email VARCHAR(120), 
	role VARCHAR(20) NOT NULL, 
	jogador_id INT, 
	created_at DATETIME, 
	last_login DATETIME, 
	foto_perfil VARCHAR(200), 
	PRIMARY KEY (id), 
	UNIQUE (username), 
	UNIQUE (email), 
	FOREIGN KEY(jogador_id) REFERENCES jogador (id)
);
INSERT INTO user VALUES(1,'admin','pbkdf2:sha256:600000$PGMw6cuCjhmkUOAk$9660f4f49b6444be3515392e1e1338089e0a5ad6af45b22c80886d34fb843c48','admin@volei.com','admin',NULL,'2026-01-29 02:36:04.543527','2026-01-31 13:44:20.907022',NULL);
INSERT INTO user VALUES(2,'samuel','pbkdf2:sha256:600000$kAe4hBx3FhhlSHvd$860cf5837fae62925c62f432e1a56776e64bd262c8a7e30ef78a985bc236d687','samuelfreitasabreu2013@gmail.com','capitao',1,'2026-01-29 04:29:24.431981','2026-01-31 03:43:03.516070',NULL);
INSERT INTO user VALUES(3,'daniel','pbkdf2:sha256:600000$kAT9lU2qQ5gOqYf2$0c2b512fb4dc139df239022f59b6c44c249f65273eb175e61a49ec1d618cdba8',NULL,'capitao',2,'2026-01-29 13:50:04.434035','2026-01-31 03:42:44.892942',NULL);
INSERT INTO user VALUES(4,'natan','pbkdf2:sha256:600000$da4SUweZBR6I8yuR$64b5d0e8c818a7b04b833b6855b6d96d2013e6fa6d03f731d98c4a83ca72c51c','natanruas@live.com','jogador',3,'2026-01-29 13:57:20.027924','2026-01-29 16:18:42.329607',NULL);
INSERT INTO user VALUES(5,'caiolima','pbkdf2:sha256:600000$kp9dSE3qITKz5Mvr$f3b3fabf0d304e29ecc5e8ac400a2da74bd3b96b540d825db2e857a48f99455e',NULL,'admin',4,'2026-01-29 13:57:58.802759','2026-01-29 16:24:52.984751',NULL);
INSERT INTO user VALUES(6,'carlin','pbkdf2:sha256:600000$KsOlDo9noI2QvP2t$98c096d21db5637e4013880466d9ac7a79ee7d5c0ae6aa83ef7746a892d853f6',NULL,'jogador',5,'2026-01-29 13:58:35.093961','2026-01-29 16:12:03.610733',NULL);
INSERT INTO user VALUES(7,'livia','pbkdf2:sha256:600000$WqT3RX3gNwsZAqYR$d8f25b7e3eb403a326ea4f0e27487e92fe8f125b6fc0924de210daf05938c40c','estrategia.alkimim@gmail.com','jogador',6,'2026-01-29 14:00:58.086690',NULL,NULL);
INSERT INTO user VALUES(8,'resende','pbkdf2:sha256:600000$IX1YTqtwtE4IiTfe$1f530ea4795bed1993fdd1436cf2022030e4a0d454f3e4a0f1bc0b7b198c6140','cadetejoaoresende@gmail.com','jogador',7,'2026-01-29 14:05:07.906135','2026-01-29 18:27:20.861530',NULL);
INSERT INTO user VALUES(9,'little_r','pbkdf2:sha256:600000$tPB1vLgHKeqFeiIk$76c134d78140e6a632bbee944e5cc8fdf26bf9c9ccfeaa7575895e4d0c1f3c72','dayvidgabriel77@gmail.com','jogador',8,'2026-01-29 14:05:51.137535',NULL,NULL);
INSERT INTO user VALUES(10,'ludmillalencar','pbkdf2:sha256:600000$QHXUz2vEwqRf2Eea$6133107be6c7489ca9011e9fbc587ab0179c1e2ad24a7561be0bcaa0ebdc8f07',NULL,'jogador',9,'2026-01-29 14:08:35.018809',NULL,NULL);
INSERT INTO user VALUES(11,'pollianesouza','pbkdf2:sha256:600000$j9dXXzjNnmdWGUW6$fb207ba0ed6fd7f236ec029f05288d3730e8bc875c670bb9827fb6a4fa49a614','polisouza13@hotmail.com','capitao',10,'2026-01-29 14:09:45.153361','2026-01-29 19:23:41.245044',NULL);
INSERT INTO user VALUES(12,'filipe ','pbkdf2:sha256:600000$qWqeWnhauxbKi4cM$ded36911912f1462510aeec880b54847d62776b540096004ff1dc883adb4eaef',NULL,'jogador',11,'2026-01-29 14:12:01.119414',NULL,NULL);
INSERT INTO user VALUES(13,'carlinhosroberto','pbkdf2:sha256:600000$2U1sT4IpahzC3OmY$f18b9cc5f64ffa741d0814db7e7023769c90bc055f56c4218aed9f11326305f9','carlinhosrobertomoctc@gmail.com','jogador',12,'2026-01-29 14:14:16.083364','2026-01-29 16:19:28.940403',NULL);
INSERT INTO user VALUES(14,'nana','pbkdf2:sha256:600000$csHbxY8IbjLrFH4f$34cda7c095251122aa0e3a09e4d82ca236d222c2d1a1e13ff8f23048e4328a7e','marianahorta0209@gmail.com','capitao',13,'2026-01-29 14:16:04.283848','2026-01-29 19:48:23.304772',NULL);
INSERT INTO user VALUES(15,'analuiza','pbkdf2:sha256:600000$gurgh4OXWgdLTjrW$73fa7e772ef227e80f5607c93a2d878c6e5d9a79c81777e18bc5f10e92a709a0',NULL,'jogador',14,'2026-01-29 14:21:46.444777','2026-01-29 16:19:10.151919',NULL);
INSERT INTO user VALUES(16,'joaoguilherme','pbkdf2:sha256:600000$mxZD6MFDWLcl2hDf$0ad1d6a194efedaca7a8890c831a575085a701fd0c7050dfa971d95334fe1836','jgpa@ymail.com','jogador',15,'2026-01-29 14:24:58.234197','2026-01-29 16:19:43.580486',NULL);
INSERT INTO user VALUES(17,'fernandarocha','pbkdf2:sha256:600000$ZFVcXqaoW2zpizcX$4c9681545e17cddd36c4e99f995310a1ef1f7bee8674b2487fccb912df56bd0d',NULL,'jogador',16,'2026-01-29 14:30:10.920338',NULL,NULL);
INSERT INTO user VALUES(18,'max','pbkdf2:sha256:600000$sdnBQLZBrpo0BdcU$9988d958d8114b0dd23142cd55f84befadd2af67ba8ad0b31c99856c58bb0339','maxxavier122@gmail.com','jogador',17,'2026-01-29 15:29:02.157018','2026-01-29 15:30:49.328251',NULL);
INSERT INTO user VALUES(19,'danielsanzio ','pbkdf2:sha256:600000$emRVicVJTiOMBded$3fe8ed38f7b35303d1696d1e8b7aa3b093656974b02e409ef971dc3fa0cd4be2',NULL,'jogador',NULL,'2026-01-29 15:59:39.380163','2026-01-29 16:00:52.254696',NULL);
INSERT INTO user VALUES(21,'brtwo','pbkdf2:sha256:600000$9czGUfFin4Jq02i8$3d7d60a13f6b45aa1b67ff816a3eedc9ea384fd3db3750953a1bbf6f8791222d',NULL,'jogador',18,'2026-01-29 16:35:49.033800',NULL,NULL);
INSERT INTO user VALUES(22,'jefferson','pbkdf2:sha256:600000$GZMvlKIrmIbJb5ah$4db91aa5a9221b4c0cc30402c97f34946862be0a3b5da5905c1479fff11929bf',NULL,'jogador',19,'2026-01-29 18:22:26.321717',NULL,NULL);
INSERT INTO user VALUES(23,'lucas','pbkdf2:sha256:600000$QhZs7466iTPZud1W$49aef1d1c1c36b8dc2512bc0af2c69a130cc100cdd381233678638a9a45e38e7',NULL,'jogador',20,'2026-01-29 18:30:35.974518',NULL,NULL);
INSERT INTO user VALUES(24,'marley','pbkdf2:sha256:600000$Vy3QMaVdoDUXCo8m$e0f99eb7a2d6bf1c0da8856021ff3063f61b69522d73a0254177cf0f8a97c1e7',NULL,'jogador',21,'2026-01-29 18:31:09.501709',NULL,NULL);
INSERT INTO user VALUES(25,'monalisa','pbkdf2:sha256:600000$FIIbNuIf8F6K5Fqk$aeb0148e4e858b0d70aed874f633c731f8bc66a536eb73187e7a46fa31253288','monalisablopes@gmail.com','jogador',22,'2026-01-29 18:31:59.324718','2026-01-29 21:50:50.445866',NULL);
INSERT INTO user VALUES(26,'jefferson.fernandes','pbkdf2:sha256:600000$JFl1w715HRd00MFG$088922c39a4e3e6bff15385b19ac8bca5d448d5ce0f7d4651b643cc5cffcda86','jefferson.farma@yahoo.com.br','jogador',23,'2026-01-29 18:33:18.399447','2026-01-29 21:49:23.588491',NULL);
INSERT INTO user VALUES(28,'rafael','pbkdf2:sha256:600000$QeGiSilxHz76X1fP$b08c7609e652e15afd02484b7d3816f39f72758a384b4de492bb7068c63b9fe0',NULL,'jogador',24,'2026-01-29 18:34:08.764215',NULL,NULL);
INSERT INTO user VALUES(30,'rafaelhudson','pbkdf2:sha256:600000$Gw1edwtB8Pyx4TyQ$e55dd4e6b7de6292371a57100c8d8ddad9cdf718fc17dd340aebfc30cba7a7d8','rafaelhudson@live.com','jogador',NULL,'2026-01-29 21:35:48.038364','2026-01-29 21:38:44.443644',NULL);
INSERT INTO user VALUES(31,'raissa','pbkdf2:sha256:600000$jezT6vxQrqyDqcAk$181c3bb365d97e8295b8cb00f3c986490a6f47fca55bd61ab60f44aa3ee4a383',NULL,'jogador',25,'2026-01-31 14:12:15.167709',NULL,NULL);
INSERT INTO user VALUES(32,'brenda','pbkdf2:sha256:600000$3wP42sXhrCXrbrgW$d9b1060abee274f255c7f8098ec49527db35e6371016c5258e27f5013d68b6fe',NULL,'jogador',26,'2026-01-31 14:13:45.860660',NULL,NULL);
DROP TABLE IF EXISTS confirmacao;
CREATE TABLE confirmacao (
	id INT NOT NULL, 
	jogador_id INT NOT NULL, 
	semana_id INT NOT NULL, 
	confirmado TINYINT(1), 
	confirmado_em DATETIME, 
	presente TINYINT(1), 
	prioridade INT, 
	PRIMARY KEY (id), 
	FOREIGN KEY(jogador_id) REFERENCES jogador (id), 
	FOREIGN KEY(semana_id) REFERENCES semana (id)
);
INSERT INTO confirmacao VALUES(1,14,5,1,'2026-01-29 19:39:26.017877',0,1);
INSERT INTO confirmacao VALUES(2,4,5,1,'2026-01-29 19:39:28.058879',0,1);
INSERT INTO confirmacao VALUES(3,12,5,1,'2026-01-29 19:39:29.930365',0,1);
INSERT INTO confirmacao VALUES(4,5,5,1,'2026-01-29 19:39:32.105520',0,1);
INSERT INTO confirmacao VALUES(5,2,5,1,'2026-01-29 19:39:33.647311',0,2);
INSERT INTO confirmacao VALUES(6,8,5,1,'2026-01-29 19:39:35.322714',0,0);
INSERT INTO confirmacao VALUES(7,18,5,1,'2026-01-29 19:39:36.529451',0,1);
INSERT INTO confirmacao VALUES(8,16,5,1,'2026-01-29 19:39:38.481020',0,1);
INSERT INTO confirmacao VALUES(9,11,5,1,'2026-01-29 19:39:39.670466',0,2);
INSERT INTO confirmacao VALUES(10,19,5,1,'2026-01-29 19:39:41.357291',0,1);
INSERT INTO confirmacao VALUES(11,23,5,1,'2026-01-29 19:39:43.705725',0,1);
INSERT INTO confirmacao VALUES(12,15,5,1,'2026-01-29 19:39:44.969591',0,1);
INSERT INTO confirmacao VALUES(13,7,5,1,'2026-01-29 19:39:46.739308',0,0);
INSERT INTO confirmacao VALUES(14,6,5,1,'2026-01-29 19:39:47.937975',0,1);
INSERT INTO confirmacao VALUES(15,20,5,1,'2026-01-29 19:39:50.401841',0,0);
INSERT INTO confirmacao VALUES(16,9,5,1,'2026-01-29 19:39:51.523613',0,1);
INSERT INTO confirmacao VALUES(17,13,5,1,'2026-01-29 19:39:54.099665',0,2);
INSERT INTO confirmacao VALUES(18,21,5,1,'2026-01-29 19:39:55.698480',0,1);
INSERT INTO confirmacao VALUES(19,17,5,1,'2026-01-29 19:39:57.009378',0,0);
INSERT INTO confirmacao VALUES(20,22,5,1,'2026-01-29 19:39:58.930895',0,1);
INSERT INTO confirmacao VALUES(21,3,5,1,'2026-01-29 19:40:00.441552',0,1);
INSERT INTO confirmacao VALUES(22,10,5,1,'2026-01-29 19:40:02.864253',0,2);
INSERT INTO confirmacao VALUES(23,24,5,1,'2026-01-29 19:40:04.545509',0,1);
INSERT INTO confirmacao VALUES(24,1,5,1,'2026-01-29 19:40:06.177042',0,2);
DROP TABLE IF EXISTS lista_espera;
CREATE TABLE lista_espera (
	id INT NOT NULL, 
	semana_id INT NOT NULL, 
	nome VARCHAR(100) NOT NULL, 
	telefone VARCHAR(20), 
	posicao_preferida VARCHAR(50), 
	adicionado_em DATETIME, 
	promovido TINYINT(1), 
	promovido_em DATETIME, 
	PRIMARY KEY (id), 
	FOREIGN KEY(semana_id) REFERENCES semana (id)
);
DROP TABLE IF EXISTS time;
CREATE TABLE time (
	id INT NOT NULL, 
	semana_id INT NOT NULL, 
	nome VARCHAR(50), 
	capitao_id INT, 
	ordem_escolha INT, 
	cor VARCHAR(20), 
	created_at DATETIME, 
	PRIMARY KEY (id), 
	FOREIGN KEY(semana_id) REFERENCES semana (id), 
	FOREIGN KEY(capitao_id) REFERENCES jogador (id)
);
INSERT INTO time VALUES(1,5,'Time 1',2,1,'#3498db','2026-01-29 19:40:34.025417');
INSERT INTO time VALUES(2,5,'Time 2',1,2,'#e74c3c','2026-01-29 19:40:34.025419');
INSERT INTO time VALUES(3,5,'Time 3',13,3,'#2ecc71','2026-01-29 19:40:34.025420');
INSERT INTO time VALUES(4,5,'Time 4',10,4,'#f39c12','2026-01-29 19:40:34.025420');
DROP TABLE IF EXISTS draft_status;
CREATE TABLE draft_status (
	id INT NOT NULL, 
	semana_id INT NOT NULL, 
	vez_capitao_id INT, 
	rodada_atual INT, 
	escolha_atual INT, 
	tempo_restante INT, 
	finalizado TINYINT(1), 
	modo_snake TINYINT(1), 
	created_at DATETIME, 
	PRIMARY KEY (id), 
	UNIQUE (semana_id), 
	FOREIGN KEY(semana_id) REFERENCES semana (id), 
	FOREIGN KEY(vez_capitao_id) REFERENCES jogador (id)
);
INSERT INTO draft_status VALUES(1,5,2,6,25,30,1,0,'2026-01-29 19:40:34.100512');
DROP TABLE IF EXISTS configuracao_global;
CREATE TABLE configuracao_global (
	id INT NOT NULL, 
	dias_semana_fixos VARCHAR(100), 
	duracao_mensalidade_dias INT, 
	senha_visitante VARCHAR(50), 
	updated_at DATETIME, 
	PRIMARY KEY (id)
);
INSERT INTO configuracao_global VALUES(1,'3',30,'volei123','2026-01-29 03:43:28.687305');
DROP TABLE IF EXISTS ciclo_mensalidade;
CREATE TABLE ciclo_mensalidade (
	id INT NOT NULL, 
	data_inicio DATE NOT NULL, 
	data_fim DATE NOT NULL, 
	ativo TINYINT(1), 
	descricao VARCHAR(200), 
	created_at DATETIME, 
	updated_at DATETIME, 
	PRIMARY KEY (id)
);
INSERT INTO ciclo_mensalidade VALUES(1,'2026-01-08','2026-02-05',1,'Janeiro','2026-01-29 02:52:29.023943','2026-01-29 03:16:40.259700');
DROP TABLE IF EXISTS pagamento_cofre;
CREATE TABLE pagamento_cofre (
	id INT NOT NULL, 
	semana_id INT NOT NULL, 
	jogador_id INT NOT NULL, 
	valor FLOAT, 
	pago TINYINT(1), 
	pago_em DATETIME, 
	metodo_pagamento VARCHAR(20), 
	observacao VARCHAR(200), 
	registrado_por VARCHAR(100), 
	created_at DATETIME, 
	updated_at DATETIME, 
	PRIMARY KEY (id), 
	FOREIGN KEY(semana_id) REFERENCES semana (id), 
	FOREIGN KEY(jogador_id) REFERENCES jogador (id)
);
INSERT INTO pagamento_cofre VALUES(1,5,7,7.0,1,'2026-01-29 20:09:40.753218','pix',NULL,NULL,'2026-01-29 16:55:32.476939','2026-01-29 20:09:40.753224');
INSERT INTO pagamento_cofre VALUES(2,5,8,7.0,1,'2026-01-29 20:14:59.239754','pix',NULL,NULL,'2026-01-29 16:55:32.576051','2026-01-29 20:14:59.239759');
INSERT INTO pagamento_cofre VALUES(3,5,11,7.0,0,NULL,'dinheiro',NULL,NULL,'2026-01-29 16:55:33.010521','2026-01-29 16:55:33.010523');
INSERT INTO pagamento_cofre VALUES(4,5,17,7.0,1,'2026-01-29 20:15:00.756709','pix',NULL,NULL,'2026-01-29 16:55:33.104993','2026-01-29 20:15:00.756715');
INSERT INTO pagamento_cofre VALUES(5,5,20,7.0,1,'2026-01-29 20:15:02.528690','pix',NULL,NULL,'2026-01-29 20:08:47.385992','2026-01-29 20:15:02.528695');
DROP TABLE IF EXISTS movimento_cofre;
CREATE TABLE movimento_cofre (
	id INT NOT NULL, 
	tipo VARCHAR(20) NOT NULL, 
	valor FLOAT NOT NULL, 
	descricao VARCHAR(200) NOT NULL, 
	semana_id INT, 
	observacao TEXT, 
	usuario VARCHAR(100), 
	created_at DATETIME, 
	PRIMARY KEY (id), 
	FOREIGN KEY(semana_id) REFERENCES semana (id)
);
INSERT INTO movimento_cofre VALUES(1,'entrada',7.0,'Pagamento de João Resende',5,'Método: pix','admin','2026-01-29 20:09:40.755350');
INSERT INTO movimento_cofre VALUES(2,'entrada',7.0,'Pagamento de Dayvid Gabriel',5,'Método: dinheiro','admin','2026-01-29 20:14:41.661796');
INSERT INTO movimento_cofre VALUES(3,'entrada',7.0,'Pagamento de Max Araújo',5,'Método: dinheiro','admin','2026-01-29 20:14:43.339500');
INSERT INTO movimento_cofre VALUES(4,'entrada',7.0,'Pagamento de Lucas',5,'Método: dinheiro','admin','2026-01-29 20:14:45.417112');
INSERT INTO movimento_cofre VALUES(5,'ajuste',-7.0,'Ajuste: Cancelamento de pagamento de Dayvid Gabriel',5,'Pagamento cancelado','admin','2026-01-29 20:14:53.652082');
INSERT INTO movimento_cofre VALUES(6,'ajuste',-7.0,'Ajuste: Cancelamento de pagamento de Max Araújo',5,'Pagamento cancelado','admin','2026-01-29 20:14:55.426714');
INSERT INTO movimento_cofre VALUES(7,'ajuste',-7.0,'Ajuste: Cancelamento de pagamento de Lucas',5,'Pagamento cancelado','admin','2026-01-29 20:14:57.451496');
INSERT INTO movimento_cofre VALUES(8,'entrada',7.0,'Pagamento de Dayvid Gabriel',5,'Método: pix','admin','2026-01-29 20:14:59.240593');
INSERT INTO movimento_cofre VALUES(9,'entrada',7.0,'Pagamento de Max Araújo',5,'Método: pix','admin','2026-01-29 20:15:00.757701');
INSERT INTO movimento_cofre VALUES(10,'entrada',7.0,'Pagamento de Lucas',5,'Método: pix','admin','2026-01-29 20:15:02.529562');
DROP TABLE IF EXISTS meta_cofre;
CREATE TABLE meta_cofre (
	id INT NOT NULL, 
	titulo VARCHAR(100) NOT NULL, 
	descricao TEXT, 
	valor_meta FLOAT NOT NULL, 
	valor_atual FLOAT, 
	data_limite DATE, 
	prioridade INT, 
	status VARCHAR(20), 
	created_at DATETIME, 
	updated_at DATETIME, 
	PRIMARY KEY (id)
);
DROP TABLE IF EXISTS escolha_draft;
CREATE TABLE escolha_draft (
	id INT NOT NULL, 
	semana_id INT NOT NULL, 
	jogador_id INT NOT NULL, 
	time_id INT NOT NULL, 
	ordem_escolha INT, 
	round_num INT, 
	escolhido_em DATETIME, 
	PRIMARY KEY (id), 
	FOREIGN KEY(semana_id) REFERENCES semana (id), 
	FOREIGN KEY(jogador_id) REFERENCES jogador (id), 
	FOREIGN KEY(time_id) REFERENCES time (id)
);
INSERT INTO escolha_draft VALUES(1,5,2,1,1,0,'2026-01-29 19:40:34.087329');
INSERT INTO escolha_draft VALUES(2,5,1,2,2,0,'2026-01-29 19:40:34.091808');
INSERT INTO escolha_draft VALUES(3,5,13,3,3,0,'2026-01-29 19:40:34.095627');
INSERT INTO escolha_draft VALUES(4,5,10,4,4,0,'2026-01-29 19:40:34.098469');
INSERT INTO escolha_draft VALUES(5,5,19,1,5,1,'2026-01-29 19:40:59.172013');
INSERT INTO escolha_draft VALUES(6,5,7,2,6,1,'2026-01-29 19:41:24.530200');
INSERT INTO escolha_draft VALUES(7,5,5,3,7,1,'2026-01-29 19:45:03.602480');
INSERT INTO escolha_draft VALUES(8,5,21,4,8,1,'2026-01-29 19:46:41.925427');
INSERT INTO escolha_draft VALUES(9,5,3,1,9,2,'2026-01-29 19:47:14.313028');
INSERT INTO escolha_draft VALUES(10,5,8,2,10,2,'2026-01-29 19:47:48.138859');
INSERT INTO escolha_draft VALUES(11,5,4,3,11,2,'2026-01-29 19:48:45.790567');
INSERT INTO escolha_draft VALUES(12,5,17,4,12,2,'2026-01-29 19:49:02.166224');
INSERT INTO escolha_draft VALUES(13,5,15,1,13,3,'2026-01-29 19:50:12.547988');
INSERT INTO escolha_draft VALUES(14,5,11,2,14,3,'2026-01-29 19:50:49.256066');
INSERT INTO escolha_draft VALUES(15,5,14,3,15,3,'2026-01-29 19:51:03.131283');
INSERT INTO escolha_draft VALUES(16,5,18,4,16,3,'2026-01-29 19:51:13.453802');
INSERT INTO escolha_draft VALUES(17,5,20,1,17,4,'2026-01-29 19:51:52.095480');
INSERT INTO escolha_draft VALUES(18,5,22,2,18,4,'2026-01-29 19:52:19.922784');
INSERT INTO escolha_draft VALUES(19,5,12,3,19,4,'2026-01-29 19:52:35.502297');
INSERT INTO escolha_draft VALUES(20,5,16,4,20,4,'2026-01-29 19:53:18.307418');
INSERT INTO escolha_draft VALUES(21,5,6,1,21,5,'2026-01-29 19:53:55.760809');
INSERT INTO escolha_draft VALUES(22,5,9,2,22,5,'2026-01-29 19:54:17.370997');
INSERT INTO escolha_draft VALUES(23,5,23,3,23,5,'2026-01-29 19:54:31.028322');
INSERT INTO escolha_draft VALUES(24,5,24,4,24,5,'2026-01-29 19:54:40.817507');
DROP TABLE IF EXISTS historico_draft;
CREATE TABLE historico_draft (
	id INT NOT NULL, 
	semana_id INT NOT NULL, 
	jogador_id INT NOT NULL, 
	time_id INT NOT NULL, 
	acao VARCHAR(50), 
	detalhes TEXT, 
	timestamp DATETIME, 
	PRIMARY KEY (id), 
	FOREIGN KEY(semana_id) REFERENCES semana (id), 
	FOREIGN KEY(jogador_id) REFERENCES jogador (id), 
	FOREIGN KEY(time_id) REFERENCES time (id)
);
INSERT INTO historico_draft VALUES(1,5,2,1,'capitao_auto','Capitão adicionado automaticamente ao time','2026-01-29 19:40:34.089350');
INSERT INTO historico_draft VALUES(2,5,1,2,'capitao_auto','Capitão adicionado automaticamente ao time','2026-01-29 19:40:34.093434');
INSERT INTO historico_draft VALUES(3,5,13,3,'capitao_auto','Capitão adicionado automaticamente ao time','2026-01-29 19:40:34.096941');
INSERT INTO historico_draft VALUES(4,5,10,4,'capitao_auto','Capitão adicionado automaticamente ao time','2026-01-29 19:40:34.100041');
INSERT INTO historico_draft VALUES(5,5,19,1,'escolhido','Escolhido por Daniel na rodada 1','2026-01-29 19:40:59.173382');
INSERT INTO historico_draft VALUES(6,5,7,2,'escolhido','Escolhido por Samuel na rodada 1','2026-01-29 19:41:24.530878');
INSERT INTO historico_draft VALUES(7,5,5,3,'escolhido','Escolhido por Mariana na rodada 1','2026-01-29 19:45:03.603173');
INSERT INTO historico_draft VALUES(8,5,21,4,'escolhido','Escolhido por Polliane na rodada 1','2026-01-29 19:46:41.926107');
INSERT INTO historico_draft VALUES(9,5,3,1,'escolhido','Escolhido por Daniel na rodada 2','2026-01-29 19:47:14.316580');
INSERT INTO historico_draft VALUES(10,5,8,2,'escolhido','Escolhido por Samuel na rodada 2','2026-01-29 19:47:48.139529');
INSERT INTO historico_draft VALUES(11,5,4,3,'escolhido','Escolhido por Mariana na rodada 2','2026-01-29 19:48:45.791212');
INSERT INTO historico_draft VALUES(12,5,17,4,'escolhido','Escolhido por Polliane na rodada 2','2026-01-29 19:49:02.166911');
INSERT INTO historico_draft VALUES(13,5,15,1,'escolhido','Escolhido por Daniel na rodada 3','2026-01-29 19:50:12.548682');
INSERT INTO historico_draft VALUES(14,5,11,2,'escolhido','Escolhido por Samuel na rodada 3','2026-01-29 19:50:49.256766');
INSERT INTO historico_draft VALUES(15,5,14,3,'escolhido','Escolhido por Mariana na rodada 3','2026-01-29 19:51:03.134062');
INSERT INTO historico_draft VALUES(16,5,18,4,'escolhido','Escolhido por Polliane na rodada 3','2026-01-29 19:51:13.454480');
INSERT INTO historico_draft VALUES(17,5,20,1,'escolhido','Escolhido por Daniel na rodada 4','2026-01-29 19:51:52.099168');
INSERT INTO historico_draft VALUES(18,5,22,2,'escolhido','Escolhido por Samuel na rodada 4','2026-01-29 19:52:19.927687');
INSERT INTO historico_draft VALUES(19,5,12,3,'escolhido','Escolhido por Mariana na rodada 4','2026-01-29 19:52:35.502971');
INSERT INTO historico_draft VALUES(20,5,16,4,'escolhido','Escolhido por Polliane na rodada 4','2026-01-29 19:53:18.310825');
INSERT INTO historico_draft VALUES(21,5,6,1,'escolhido','Escolhido por Daniel na rodada 5','2026-01-29 19:53:55.762241');
INSERT INTO historico_draft VALUES(22,5,9,2,'escolhido','Escolhido por Samuel na rodada 5','2026-01-29 19:54:17.371682');
INSERT INTO historico_draft VALUES(23,5,23,3,'escolhido','Escolhido por Mariana na rodada 5','2026-01-29 19:54:31.030083');
INSERT INTO historico_draft VALUES(24,5,24,4,'escolhido','Escolhido por Polliane na rodada 5','2026-01-29 19:54:40.818192');

SET FOREIGN_KEY_CHECKS=1;
