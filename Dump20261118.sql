-- MySQL dump 10.13  Distrib 8.0.46, for Win64 (x86_64)
--
-- Host: gateway01.ap-northeast-1.prod.aws.tidbcloud.com    Database: dbptit
-- ------------------------------------------------------
-- Server version	8.0.11-TiDB-v8.5.3-serverless

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
-- Table structure for table `baidoxe`
--

DROP TABLE IF EXISTS `baidoxe`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `baidoxe` (
  `id` int NOT NULL AUTO_INCREMENT,
  `tenbaido` varchar(20) DEFAULT NULL,
  `diadiem` varchar(20) NOT NULL,
  PRIMARY KEY (`id`) /*T![clustered_index] CLUSTERED */
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin AUTO_INCREMENT=30001;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `baidoxe`
--

LOCK TABLES `baidoxe` WRITE;
/*!40000 ALTER TABLE `baidoxe` DISABLE KEYS */;
INSERT INTO `baidoxe` VALUES (1,'bãi đố ô tô','sân trường PTIT'),(2,'bãi đố xe máy','nhà để xe cạnh PTIT'),(3,'bãi đố xe đạp','sau tòa C PTIT');
/*!40000 ALTER TABLE `baidoxe` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `banggia`
--

DROP TABLE IF EXISTS `banggia`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `banggia` (
  `id` int NOT NULL AUTO_INCREMENT,
  `loaive` varchar(5) DEFAULT NULL,
  `dongia` int DEFAULT NULL,
  `idlpt` int DEFAULT NULL,
  `idlkh` int DEFAULT NULL,
  PRIMARY KEY (`id`) /*T![clustered_index] CLUSTERED */,
  KEY `fk_banggia_loaiphuongtien` (`idlpt`),
  KEY `fk_banggia_loaikhachhang` (`idlkh`),
  CONSTRAINT `fk_banggia_loaiphuongtien` FOREIGN KEY (`idlpt`) REFERENCES `loaiphuongtien` (`id`),
  CONSTRAINT `fk_banggia_loaikhachhang` FOREIGN KEY (`idlkh`) REFERENCES `loaikhachhang` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin AUTO_INCREMENT=30001;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `banggia`
--

LOCK TABLES `banggia` WRITE;
/*!40000 ALTER TABLE `banggia` DISABLE KEYS */;
INSERT INTO `banggia` VALUES (1,'ngày',3000,1,NULL),(2,'ngày',5000,2,NULL),(3,'ngày',10000,3,NULL),(4,'tháng',72000,1,2),(5,'tháng',120000,2,2),(6,'tháng',240000,3,2),(7,'tháng',72000,1,1),(8,'tháng',192000,2,1),(9,'tháng',288000,3,1);
/*!40000 ALTER TABLE `banggia` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `khachhang`
--

DROP TABLE IF EXISTS `khachhang`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `khachhang` (
  `id` int NOT NULL AUTO_INCREMENT,
  `hoten` varchar(20) NOT NULL,
  `sdt` varchar(20) NOT NULL,
  `cccd` varchar(15) NOT NULL,
  `idlkh` int DEFAULT NULL,
  PRIMARY KEY (`id`) /*T![clustered_index] CLUSTERED */,
  UNIQUE KEY `cccd` (`cccd`),
  KEY `fk_khachhang_loaikhachhang` (`idlkh`),
  CONSTRAINT `fk_khachhang_loaikhachhang` FOREIGN KEY (`idlkh`) REFERENCES `loaikhachhang` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `khachhang`
--

LOCK TABLES `khachhang` WRITE;
/*!40000 ALTER TABLE `khachhang` DISABLE KEYS */;
/*!40000 ALTER TABLE `khachhang` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `khuvucdo`
--

DROP TABLE IF EXISTS `khuvucdo`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `khuvucdo` (
  `id` int NOT NULL AUTO_INCREMENT,
  `idbdx` int DEFAULT NULL,
  `ten` varchar(5) NOT NULL,
  PRIMARY KEY (`id`) /*T![clustered_index] CLUSTERED */,
  KEY `khuvucdo` (`idbdx`),
  CONSTRAINT `fk_khuvucdo_baidoxe` FOREIGN KEY (`idbdx`) REFERENCES `baidoxe` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin AUTO_INCREMENT=30001;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `khuvucdo`
--

LOCK TABLES `khuvucdo` WRITE;
/*!40000 ALTER TABLE `khuvucdo` DISABLE KEYS */;
INSERT INTO `khuvucdo` VALUES (1,1,'A'),(2,1,'B'),(3,1,'C'),(4,1,'D'),(5,1,'E'),(6,1,'F'),(7,1,'G'),(8,1,'H'),(9,1,'I'),(10,1,'J'),(11,2,'A'),(12,2,'B'),(13,2,'C'),(14,2,'D'),(15,2,'E'),(16,2,'F'),(17,2,'G'),(18,2,'H'),(19,2,'I'),(20,2,'J'),(21,2,'K'),(22,2,'L'),(23,2,'M'),(24,2,'N'),(25,2,'O'),(26,2,'P'),(27,2,'Q'),(28,2,'R'),(29,2,'S'),(30,2,'T'),(31,3,'A'),(32,3,'B'),(33,3,'C'),(34,3,'D'),(35,3,'E');
/*!40000 ALTER TABLE `khuvucdo` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `loaikhachhang`
--

DROP TABLE IF EXISTS `loaikhachhang`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `loaikhachhang` (
  `id` int NOT NULL AUTO_INCREMENT,
  `tenloai` varchar(10) DEFAULT NULL,
  PRIMARY KEY (`id`) /*T![clustered_index] CLUSTERED */
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin AUTO_INCREMENT=30001;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `loaikhachhang`
--

LOCK TABLES `loaikhachhang` WRITE;
/*!40000 ALTER TABLE `loaikhachhang` DISABLE KEYS */;
INSERT INTO `loaikhachhang` VALUES (1,'giảng viên'),(2,'sinh viên');
/*!40000 ALTER TABLE `loaikhachhang` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `loaiphuongtien`
--

DROP TABLE IF EXISTS `loaiphuongtien`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `loaiphuongtien` (
  `id` int NOT NULL AUTO_INCREMENT,
  `tenloai` varchar(10) DEFAULT NULL,
  PRIMARY KEY (`id`) /*T![clustered_index] CLUSTERED */
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin AUTO_INCREMENT=30001;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `loaiphuongtien`
--

LOCK TABLES `loaiphuongtien` WRITE;
/*!40000 ALTER TABLE `loaiphuongtien` DISABLE KEYS */;
INSERT INTO `loaiphuongtien` VALUES (1,'xe đạp'),(2,'xe máy'),(3,'ô tô');
/*!40000 ALTER TABLE `loaiphuongtien` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `luotdo`
--

DROP TABLE IF EXISTS `luotdo`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `luotdo` (
  `id` int NOT NULL AUTO_INCREMENT,
  `idvtd` int NOT NULL,
  `giovao` datetime NOT NULL,
  `giora` datetime NOT NULL,
  `idnv` int NOT NULL,
  `idpt` int DEFAULT NULL,
  `idtx` int DEFAULT NULL,
  `idbg` int DEFAULT NULL,
  PRIMARY KEY (`id`) /*T![clustered_index] CLUSTERED */,
  KEY `fk_luotdo_vitrido` (`idvtd`),
  KEY `fk_luotdo_nhanvien` (`idnv`),
  KEY `fk_luotdo_phuongtien` (`idpt`),
  KEY `fk_luotdo_thexe` (`idtx`),
  KEY `fk_luotdo_banggia` (`idbg`),
  CONSTRAINT `fk_luotdo_vitrido` FOREIGN KEY (`idvtd`) REFERENCES `vitrido` (`id`),
  CONSTRAINT `fk_luotdo_nhanvien` FOREIGN KEY (`idnv`) REFERENCES `nhanvien` (`id`),
  CONSTRAINT `fk_luotdo_phuongtien` FOREIGN KEY (`idpt`) REFERENCES `phuongtien` (`id`),
  CONSTRAINT `fk_luotdo_thexe` FOREIGN KEY (`idtx`) REFERENCES `thexe` (`id`),
  CONSTRAINT `fk_luotdo_banggia` FOREIGN KEY (`idbg`) REFERENCES `banggia` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `luotdo`
--

LOCK TABLES `luotdo` WRITE;
/*!40000 ALTER TABLE `luotdo` DISABLE KEYS */;
/*!40000 ALTER TABLE `luotdo` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `nhanvien`
--

DROP TABLE IF EXISTS `nhanvien`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `nhanvien` (
  `id` int NOT NULL AUTO_INCREMENT,
  `idbdx` int DEFAULT NULL,
  `hoten` varchar(20) NOT NULL,
  `diachi` varchar(20) DEFAULT NULL,
  `ngaysinh` date DEFAULT NULL,
  `chucvu` varchar(10) NOT NULL,
  `sdt` varchar(10) NOT NULL,
  `ngaybatdau` date DEFAULT NULL,
  `email` varchar(20) DEFAULT NULL,
  `cccd` varchar(15) DEFAULT NULL,
  PRIMARY KEY (`id`) /*T![clustered_index] CLUSTERED */,
  KEY `nhanvien` (`idbdx`),
  UNIQUE KEY `uk_cccd` (`cccd`),
  CONSTRAINT `fk_nhanvien_baidoxe` FOREIGN KEY (`idbdx`) REFERENCES `baidoxe` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `nhanvien`
--

LOCK TABLES `nhanvien` WRITE;
/*!40000 ALTER TABLE `nhanvien` DISABLE KEYS */;
/*!40000 ALTER TABLE `nhanvien` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `phuongtien`
--

DROP TABLE IF EXISTS `phuongtien`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `phuongtien` (
  `id` int NOT NULL AUTO_INCREMENT,
  `bienso` varchar(8) DEFAULT NULL,
  `idlpt` int DEFAULT NULL,
  PRIMARY KEY (`id`) /*T![clustered_index] CLUSTERED */,
  UNIQUE KEY `bienso` (`bienso`),
  KEY `fk_phuongtien_loaiphuongtien` (`idlpt`),
  CONSTRAINT `fk_phuongtien_loaiphuongtien` FOREIGN KEY (`idlpt`) REFERENCES `loaiphuongtien` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `phuongtien`
--

LOCK TABLES `phuongtien` WRITE;
/*!40000 ALTER TABLE `phuongtien` DISABLE KEYS */;
/*!40000 ALTER TABLE `phuongtien` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `thanhtoan`
--

DROP TABLE IF EXISTS `thanhtoan`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `thanhtoan` (
  `id` int NOT NULL AUTO_INCREMENT,
  `idld` int NOT NULL,
  `chiphi` int NOT NULL,
  `giothanhtoan` datetime NOT NULL,
  `trangthai` varchar(10) NOT NULL,
  `idnv` int NOT NULL,
  `loaithanhtoan` tinyint(1) DEFAULT NULL,
  `idvt` int DEFAULT NULL,
  PRIMARY KEY (`id`) /*T![clustered_index] CLUSTERED */,
  KEY `fk_thoantoan_luotdo` (`idld`),
  KEY `fk_thanhtoan_nhanvien` (`idnv`),
  KEY `fk_thanhtoan_vethang` (`idvt`),
  CONSTRAINT `fk_thoantoan_luotdo` FOREIGN KEY (`idld`) REFERENCES `luotdo` (`id`),
  CONSTRAINT `fk_thanhtoan_nhanvien` FOREIGN KEY (`idnv`) REFERENCES `nhanvien` (`id`),
  CONSTRAINT `fk_thanhtoan_vethang` FOREIGN KEY (`idvt`) REFERENCES `vethang` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `thanhtoan`
--

LOCK TABLES `thanhtoan` WRITE;
/*!40000 ALTER TABLE `thanhtoan` DISABLE KEYS */;
/*!40000 ALTER TABLE `thanhtoan` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `thexe`
--

DROP TABLE IF EXISTS `thexe`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `thexe` (
  `id` int NOT NULL AUTO_INCREMENT,
  `maso` varchar(10) DEFAULT NULL,
  `trangthai` tinyint(1) DEFAULT NULL,
  PRIMARY KEY (`id`) /*T![clustered_index] CLUSTERED */
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `thexe`
--

LOCK TABLES `thexe` WRITE;
/*!40000 ALTER TABLE `thexe` DISABLE KEYS */;
/*!40000 ALTER TABLE `thexe` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `vethang`
--

DROP TABLE IF EXISTS `vethang`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `vethang` (
  `id` int NOT NULL AUTO_INCREMENT,
  `ngaybatdau` date DEFAULT NULL,
  `ngayketthuc` date DEFAULT NULL,
  `idtx` int DEFAULT NULL,
  `idpt` int DEFAULT NULL,
  `idbg` int DEFAULT NULL,
  `idkh` int DEFAULT NULL,
  PRIMARY KEY (`id`) /*T![clustered_index] CLUSTERED */,
  KEY `fk_vethang_thexe` (`idtx`),
  KEY `fk_vethang_phuongtien` (`idpt`),
  KEY `fk_vethang_banggia` (`idbg`),
  KEY `fk_vethang_khachhang` (`idkh`),
  CONSTRAINT `fk_vethang_thexe` FOREIGN KEY (`idtx`) REFERENCES `thexe` (`id`),
  CONSTRAINT `fk_vethang_phuongtien` FOREIGN KEY (`idpt`) REFERENCES `phuongtien` (`id`),
  CONSTRAINT `fk_vethang_banggia` FOREIGN KEY (`idbg`) REFERENCES `banggia` (`id`),
  CONSTRAINT `fk_vethang_khachhang` FOREIGN KEY (`idkh`) REFERENCES `khachhang` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `vethang`
--

LOCK TABLES `vethang` WRITE;
/*!40000 ALTER TABLE `vethang` DISABLE KEYS */;
/*!40000 ALTER TABLE `vethang` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `vitrido`
--

DROP TABLE IF EXISTS `vitrido`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `vitrido` (
  `id` int NOT NULL AUTO_INCREMENT,
  `idkvd` int DEFAULT NULL,
  `sothutu` int DEFAULT NULL,
  `trangthai` tinyint(1) DEFAULT NULL,
  PRIMARY KEY (`id`) /*T![clustered_index] CLUSTERED */,
  KEY `vitrido` (`idkvd`),
  UNIQUE KEY `unique_khu_stt` (`idkvd`,`sothutu`),
  CONSTRAINT `fk_vitri_khuvuc` FOREIGN KEY (`idkvd`) REFERENCES `khuvucdo` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin AUTO_INCREMENT=30001;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `vitrido`
--

LOCK TABLES `vitrido` WRITE;
/*!40000 ALTER TABLE `vitrido` DISABLE KEYS */;
INSERT INTO `vitrido` VALUES (1,1,1,1),(2,1,2,1),(3,1,3,1),(4,1,4,1),(5,1,5,1);
/*!40000 ALTER TABLE `vitrido` ENABLE KEYS */;
UNLOCK TABLES;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2026-11-18 14:32:19
