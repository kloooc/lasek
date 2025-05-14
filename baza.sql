-- MySQL dump 10.13  Distrib 8.0.41, for Win64 (x86_64)
--
-- Host: 127.0.0.1    Database: system_rezerwacji
-- ------------------------------------------------------
-- Server version	8.0.41

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!50503 SET NAMES utf8 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table `rezerwacje`
--

DROP TABLE IF EXISTS `rezerwacje`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `rezerwacje` (
  `id_rezerwacji` int NOT NULL AUTO_INCREMENT,
  `id_user` int NOT NULL,
  `id_stolika` int NOT NULL,
  `data` datetime NOT NULL,
  `oplacony` tinyint(1) NOT NULL DEFAULT '0',
  `data_konca` datetime NOT NULL DEFAULT '2025-01-01 00:00:00',
  PRIMARY KEY (`id_rezerwacji`),
  KEY `id_user` (`id_user`),
  KEY `id_stolika` (`id_stolika`),
  CONSTRAINT `rezerwacje_ibfk_1` FOREIGN KEY (`id_user`) REFERENCES `uzytkownicy` (`id_user`),
  CONSTRAINT `rezerwacje_ibfk_2` FOREIGN KEY (`id_stolika`) REFERENCES `stoliki` (`id_stolika`)
) ENGINE=InnoDB AUTO_INCREMENT=8 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `rezerwacje`
--

LOCK TABLES `rezerwacje` WRITE;
/*!40000 ALTER TABLE `rezerwacje` DISABLE KEYS */;
INSERT INTO `rezerwacje` VALUES (1,2,1,'2025-04-10 18:30:00',1,'2025-04-10 20:30:00'),(2,3,3,'2025-04-11 20:00:00',1,'2025-04-11 22:00:00'),(4,3,2,'2025-05-14 19:00:00',1,'2025-05-14 21:00:00'),(7,2,1,'2025-05-15 15:00:00',1,'2025-05-15 17:00:00');
/*!40000 ALTER TABLE `rezerwacje` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `stoliki`
--

DROP TABLE IF EXISTS `stoliki`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `stoliki` (
  `id_stolika` int NOT NULL AUTO_INCREMENT,
  `ilosc_miejsc` int NOT NULL,
  PRIMARY KEY (`id_stolika`),
  CONSTRAINT `stoliki_chk_1` CHECK ((`ilosc_miejsc` > 0))
) ENGINE=InnoDB AUTO_INCREMENT=20 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `stoliki`
--

LOCK TABLES `stoliki` WRITE;
/*!40000 ALTER TABLE `stoliki` DISABLE KEYS */;
INSERT INTO `stoliki` VALUES (1,5),(2,5),(3,5),(4,5),(5,4),(6,4),(7,4),(8,4),(9,10),(10,10),(11,10),(12,10),(13,2),(14,2);
/*!40000 ALTER TABLE `stoliki` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `uzytkownicy`
--

DROP TABLE IF EXISTS `uzytkownicy`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `uzytkownicy` (
  `id_user` int NOT NULL AUTO_INCREMENT,
  `email` varchar(100) NOT NULL,
  `password` varchar(100) NOT NULL,
  `imie` varchar(50) NOT NULL,
  `nazwisko` varchar(50) NOT NULL,
  `status` enum('admin','klient') NOT NULL,
  PRIMARY KEY (`id_user`),
  UNIQUE KEY `email` (`email`)
) ENGINE=InnoDB AUTO_INCREMENT=7 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `uzytkownicy`
--

LOCK TABLES `uzytkownicy` WRITE;
/*!40000 ALTER TABLE `uzytkownicy` DISABLE KEYS */;
INSERT INTO `uzytkownicy` VALUES (1,'admin@restauracja.pl','admin123','Anna','Nowak','admin'),(2,'klient1@example.com','haslo1','Jan','Kowalski','klient'),(3,'klient2@example.com','haslo2','Ewa','Wiśniewska','klient'),(5,'admin1@restauracja.pl','123123','123123','123321','klient');
/*!40000 ALTER TABLE `uzytkownicy` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Dumping events for database 'system_rezerwacji'
--

--
-- Dumping routines for database 'system_rezerwacji'
--
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2025-05-14 22:04:23
