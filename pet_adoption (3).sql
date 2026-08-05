-- phpMyAdmin SQL Dump
-- version 5.2.1
-- https://www.phpmyadmin.net/
--
-- 主機： 127.0.0.1
-- 產生時間： 2026-08-05 08:52:06
-- 伺服器版本： 10.4.32-MariaDB
-- PHP 版本： 8.2.12

SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
START TRANSACTION;
SET time_zone = "+00:00";


/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;

--
-- 資料庫： `pet_adoption`
--

-- --------------------------------------------------------

--
-- 資料表結構 `adopter_ratings`
--

CREATE TABLE `adopter_ratings` (
  `id` int(11) NOT NULL,
  `adopter` varchar(100) NOT NULL,
  `rater` varchar(100) NOT NULL,
  `pet_name` varchar(100) DEFAULT NULL,
  `responsibility` tinyint(4) NOT NULL,
  `tracking` tinyint(4) NOT NULL,
  `environment` tinyint(4) NOT NULL,
  `care` tinyint(4) NOT NULL,
  `score` decimal(3,2) NOT NULL,
  `comment` text DEFAULT NULL,
  `created_at` datetime NOT NULL DEFAULT current_timestamp(),
  `updated_at` datetime NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- 資料表結構 `adoption_tracking`
--

CREATE TABLE `adoption_tracking` (
  `id` int(11) NOT NULL,
  `application_id` int(11) DEFAULT NULL COMMENT '申請ID',
  `chip_number` varchar(30) DEFAULT NULL COMMENT '晶片號碼',
  `adopter_id` int(11) DEFAULT NULL COMMENT '領養者ID',
  `tracking_date` date DEFAULT NULL COMMENT '追蹤日期',
  `status` varchar(50) DEFAULT NULL COMMENT '追蹤狀態',
  `notes` text DEFAULT NULL COMMENT '備註',
  `next_tracking_date` date DEFAULT NULL COMMENT '下次追蹤日期',
  `created_at` timestamp NOT NULL DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- 資料表結構 `animals`
--

CREATE TABLE `animals` (
  `chip_number` varchar(30) NOT NULL COMMENT '晶片號碼',
  `name` varchar(100) DEFAULT NULL COMMENT '動物名稱',
  `species` varchar(50) DEFAULT NULL COMMENT '動物類別',
  `gender` varchar(10) DEFAULT NULL COMMENT '動物性別',
  `breed` varchar(100) DEFAULT NULL COMMENT '品種／物種',
  `coat_color` varchar(50) DEFAULT NULL COMMENT '毛色',
  `size` varchar(20) DEFAULT NULL COMMENT '體型',
  `surrender_reason` text DEFAULT NULL COMMENT '讓渡原因',
  `owner_name` varchar(100) DEFAULT NULL COMMENT '飼主姓名',
  `shelter_name` varchar(150) DEFAULT NULL COMMENT '公告收容所',
  `announcement_date` date DEFAULT NULL COMMENT '公告時間',
  `age_group` varchar(20) DEFAULT NULL,
  `personality` varchar(50) DEFAULT NULL,
  `health_status` varchar(100) DEFAULT NULL,
  `is_neutered` tinyint(1) NOT NULL DEFAULT 0,
  `owner_type` varchar(30) DEFAULT NULL,
  `description` text DEFAULT NULL,
  `location` varchar(100) DEFAULT NULL,
  `photo_url` text DEFAULT NULL,
  `status` varchar(20) NOT NULL DEFAULT 'available',
  `foster_id` int(11) DEFAULT NULL,
  `created_at` datetime NOT NULL DEFAULT current_timestamp(),
  `updated_at` datetime NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- 傾印資料表的資料 `animals`
--

INSERT INTO `animals` (`chip_number`, `name`, `species`, `gender`, `breed`, `coat_color`, `size`, `surrender_reason`, `owner_name`, `shelter_name`, `announcement_date`, `age_group`, `personality`, `health_status`, `is_neutered`, `owner_type`, `description`, `location`, `photo_url`, `status`, `foster_id`, `created_at`, `updated_at`) VALUES
('0', '0', '貓', '公', NULL, NULL, '小型', NULL, 'test1', NULL, '2026-08-04', '成年', '安靜', '健康', 1, '收容所', '', '台北市', NULL, 'trial', 3, '2026-08-04 15:04:25', '2026-08-04 15:40:38');

-- --------------------------------------------------------

--
-- 資料表結構 `applications`
--

CREATE TABLE `applications` (
  `id` int(11) NOT NULL,
  `user_id` int(11) DEFAULT NULL,
  `chip_number` varchar(30) DEFAULT NULL,
  `animal_id` int(11) DEFAULT NULL,
  `status` varchar(20) DEFAULT 'pending',
  `created_at` datetime DEFAULT current_timestamp(),
  `adopter_name` varchar(50) DEFAULT NULL,
  `phone` varchar(20) DEFAULT NULL,
  `living_environment` varchar(50) DEFAULT NULL,
  `pet_experience` varchar(20) DEFAULT NULL,
  `message` text DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- 傾印資料表的資料 `applications`
--

INSERT INTO `applications` (`id`, `user_id`, `chip_number`, `animal_id`, `status`, `created_at`, `adopter_name`, `phone`, `living_environment`, `pet_experience`, `message`) VALUES
(1, 2, '900138000785639', NULL, 'pending', '2026-08-04 14:49:20', '133test', '0922222222', '套房', '豐富經驗', ''),
(2, 2, '0', NULL, 'trial', '2026-08-04 15:04:45', '133test', '0922222222', '套房', '豐富經驗', '');

-- --------------------------------------------------------

--
-- 資料表結構 `chat_messages`
--

CREATE TABLE `chat_messages` (
  `id` int(11) NOT NULL,
  `pet_name` varchar(100) NOT NULL,
  `sender` varchar(100) NOT NULL,
  `receiver` varchar(100) NOT NULL,
  `message` text NOT NULL,
  `created_at` datetime NOT NULL DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- 傾印資料表的資料 `chat_messages`
--

INSERT INTO `chat_messages` (`id`, `pet_name`, `sender`, `receiver`, `message`, `created_at`) VALUES
(1, '0', 'test1', '133test', 'hi', '2026-08-04 15:39:43'),
(2, '0', '133test', 'test1', 'hi', '2026-08-04 15:40:05');

-- --------------------------------------------------------

--
-- 資料表結構 `educational_articles`
--

CREATE TABLE `educational_articles` (
  `id` int(11) NOT NULL,
  `title` varchar(200) DEFAULT NULL COMMENT '標題',
  `content` text DEFAULT NULL COMMENT '內容',
  `category` varchar(50) DEFAULT NULL COMMENT '分類(飼養知識/責任宣導)',
  `author` varchar(100) DEFAULT NULL COMMENT '作者',
  `views` int(11) DEFAULT 0 COMMENT '瀏覽次數',
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `updated_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- 資料表結構 `faq`
--

CREATE TABLE `faq` (
  `id` int(11) NOT NULL,
  `question` text DEFAULT NULL COMMENT '問題',
  `answer` text DEFAULT NULL COMMENT '答案',
  `category` varchar(50) DEFAULT NULL COMMENT '分類',
  `order_num` int(11) DEFAULT 0 COMMENT '排序',
  `created_at` timestamp NOT NULL DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- 資料表結構 `notifications`
--

CREATE TABLE `notifications` (
  `id` int(11) NOT NULL,
  `user_account` varchar(100) NOT NULL,
  `title` varchar(150) NOT NULL,
  `content` text DEFAULT NULL,
  `created_at` datetime NOT NULL DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- 傾印資料表的資料 `notifications`
--

INSERT INTO `notifications` (`id`, `user_account`, `title`, `content`, `created_at`) VALUES
(1, '133test', '新的聊天訊息', 'test1 傳送了關於 0 的訊息。', '2026-08-04 15:39:43'),
(2, 'test1', '新的聊天訊息', '133test 傳送了關於 0 的訊息。', '2026-08-04 15:40:05'),
(3, '133test', '試養中', '你申請的 0 狀態已更新為：試養中。', '2026-08-04 15:40:38');

-- --------------------------------------------------------

--
-- 資料表結構 `users`
--

CREATE TABLE `users` (
  `id` int(11) NOT NULL,
  `name` varchar(50) DEFAULT NULL,
  `email` varchar(100) DEFAULT NULL,
  `password` varchar(255) DEFAULT NULL,
  `created_at` datetime DEFAULT current_timestamp(),
  `role` enum('adopter','foster','admin') DEFAULT 'adopter' COMMENT '角色：領養者/送養者/管理員',
  `phone` varchar(20) DEFAULT NULL COMMENT '電話',
  `address` text DEFAULT NULL COMMENT '地址',
  `updated_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  `living_environment` varchar(50) DEFAULT NULL COMMENT '居住環境',
  `pet_experience` varchar(20) DEFAULT NULL COMMENT '是否有養寵物經驗',
  `can_keep_pet` tinyint(1) DEFAULT 1,
  `daily_time` varchar(30) DEFAULT NULL,
  `pref_type` varchar(20) DEFAULT NULL,
  `pref_age` varchar(20) DEFAULT NULL,
  `pref_gender` varchar(10) DEFAULT NULL,
  `family_child` varchar(20) DEFAULT NULL,
  `personality_pref` varchar(30) DEFAULT NULL,
  `can_cross_city` tinyint(1) DEFAULT 0,
  `can_take_special` tinyint(1) DEFAULT 0,
  `housing_size` varchar(30) DEFAULT NULL,
  `travel_frequency` varchar(30) DEFAULT NULL,
  `living_stability` varchar(30) DEFAULT NULL,
  `monthly_budget` varchar(30) DEFAULT NULL,
  `child_age` varchar(20) DEFAULT NULL,
  `has_other_pets` varchar(30) DEFAULT NULL,
  `allergy_tolerance` varchar(30) DEFAULT NULL,
  `only_neutered` tinyint(1) DEFAULT 0
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- 傾印資料表的資料 `users`
--

INSERT INTO `users` (`id`, `name`, `email`, `password`, `created_at`, `role`, `phone`, `address`, `updated_at`, `living_environment`, `pet_experience`, `can_keep_pet`, `daily_time`, `pref_type`, `pref_age`, `pref_gender`, `family_child`, `personality_pref`, `can_cross_city`, `can_take_special`, `housing_size`, `travel_frequency`, `living_stability`, `monthly_budget`, `child_age`, `has_other_pets`, `allergy_tolerance`, `only_neutered`) VALUES
(1, '1', '1', 'c4ca4238a0b923820dcc509a6f75849b', '2026-04-25 14:55:36', 'adopter', '1', '1', '2026-04-25 06:55:36', NULL, NULL, 1, NULL, NULL, NULL, NULL, NULL, NULL, 0, 0, NULL, NULL, NULL, NULL, NULL, NULL, NULL, 0),
(2, '133test', 'uu@gmail.com', '39143d00293abcdd35fad07943e667fa', '2026-07-31 22:14:01', 'adopter', '0922222222', '台北市', '2026-07-31 14:14:01', '套房', '豐富經驗', 1, '3小時以上', '狗', '幼年', '公', '無小孩', '親人', 1, 1, '中等空間', '很少出差', '定居', '3000元以下', '無小孩', '沒有其他寵物', '可接受', 0),
(3, 'test1', 'test@gmail.com', '5a105e8b9d40e1329780d62ea2265d8a', '2026-08-04 14:53:49', 'foster', '0922222222', '新北市', '2026-08-04 06:53:49', '公寓', '無經驗', 1, '1小時以內', '貓', '成年', '公', '無小孩', '安靜', 0, 0, '中等空間', '偶爾出差', '定居', '3000~6000元', '無小孩', '沒有其他寵物', '普通', 0);

--
-- 已傾印資料表的索引
--

--
-- 資料表索引 `adopter_ratings`
--
ALTER TABLE `adopter_ratings`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `uk_rating` (`adopter`,`rater`,`pet_name`),
  ADD KEY `idx_rating_adopter` (`adopter`);

--
-- 資料表索引 `adoption_tracking`
--
ALTER TABLE `adoption_tracking`
  ADD PRIMARY KEY (`id`),
  ADD KEY `application_id` (`application_id`),
  ADD KEY `animal_id` (`chip_number`),
  ADD KEY `adopter_id` (`adopter_id`);

--
-- 資料表索引 `animals`
--
ALTER TABLE `animals`
  ADD PRIMARY KEY (`chip_number`);

--
-- 資料表索引 `applications`
--
ALTER TABLE `applications`
  ADD PRIMARY KEY (`id`);

--
-- 資料表索引 `chat_messages`
--
ALTER TABLE `chat_messages`
  ADD PRIMARY KEY (`id`),
  ADD KEY `idx_chat_room` (`pet_name`,`sender`,`receiver`),
  ADD KEY `idx_chat_created` (`created_at`);

--
-- 資料表索引 `educational_articles`
--
ALTER TABLE `educational_articles`
  ADD PRIMARY KEY (`id`);

--
-- 資料表索引 `faq`
--
ALTER TABLE `faq`
  ADD PRIMARY KEY (`id`);

--
-- 資料表索引 `notifications`
--
ALTER TABLE `notifications`
  ADD PRIMARY KEY (`id`),
  ADD KEY `idx_notification_user` (`user_account`,`created_at`);

--
-- 資料表索引 `users`
--
ALTER TABLE `users`
  ADD PRIMARY KEY (`id`);

--
-- 在傾印的資料表使用自動遞增(AUTO_INCREMENT)
--

--
-- 使用資料表自動遞增(AUTO_INCREMENT) `adopter_ratings`
--
ALTER TABLE `adopter_ratings`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT;

--
-- 使用資料表自動遞增(AUTO_INCREMENT) `adoption_tracking`
--
ALTER TABLE `adoption_tracking`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT;

--
-- 使用資料表自動遞增(AUTO_INCREMENT) `applications`
--
ALTER TABLE `applications`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=3;

--
-- 使用資料表自動遞增(AUTO_INCREMENT) `chat_messages`
--
ALTER TABLE `chat_messages`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=3;

--
-- 使用資料表自動遞增(AUTO_INCREMENT) `educational_articles`
--
ALTER TABLE `educational_articles`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT;

--
-- 使用資料表自動遞增(AUTO_INCREMENT) `faq`
--
ALTER TABLE `faq`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT;

--
-- 使用資料表自動遞增(AUTO_INCREMENT) `notifications`
--
ALTER TABLE `notifications`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=4;

--
-- 使用資料表自動遞增(AUTO_INCREMENT) `users`
--
ALTER TABLE `users`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=4;

--
-- 已傾印資料表的限制式
--

--
-- 資料表的限制式 `adoption_tracking`
--
ALTER TABLE `adoption_tracking`
  ADD CONSTRAINT `adoption_tracking_ibfk_1` FOREIGN KEY (`application_id`) REFERENCES `applications` (`id`),
  ADD CONSTRAINT `adoption_tracking_ibfk_3` FOREIGN KEY (`adopter_id`) REFERENCES `users` (`id`);
COMMIT;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
