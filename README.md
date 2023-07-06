# 新片场爬虫项目

## 项目目标

目标数据：爬取新片场广告页面第 11 ~ 15 页的数据，具体包括：
  - 基本数据：视频标题、点赞量、收藏量。
  - 评论数据：视频详情页中的评论数据。
  - 播放地址：视频所有清晰度的播放地址。

存储需求：存储在 MySQL 中，可用 SQL 语句查询到一个视频的所有数据。

所用技术栈：Scrapy、BeautifulSoup4、XPath、CSS Selector、JSON、MySQL、Logging

## 项目部署说明

 - 在 DBMS 中创建 xpc 数据库。

```sql
CREATE DATABASE IF NOT EXISTS xpc charset='utf8mb4';
```

 - 创建数据表。

```sql
USE xpc;

DROP TABLE IF EXISTS video_base_info;
CREATE TABLE IF NOT EXISTS video_base_info (
    `article_id` INT PRIMARY KEY,
    `title` VARCHAR(255),
    `like_count` VARCHAR(255),
    `collection_count` VARCHAR(255)
);

DROP TABLE IF EXISTS comment;
CREATE TABLE IF NOT EXISTS comment (
    `comment_id` INT,
    `article_id` INT,
    `content` TEXT,
    `timestamp` TIMESTAMP
);

DROP TABLE IF EXISTS video_url;
CREATE TABLE IF NOT EXISTS video_url (
    `article_id` INT,
    `quality` VARCHAR(255),
    `url` VARCHAR(255)
);
```
 - 在 profile.json 中配置数据库连接信息与用于登录新片场的手机号和密码。

## 实现流程概述

1. 在 `profile.json` 配置文件中编写新片场的账户信息，爬虫启动时通过 Selenium 程序模拟登录，并获取登录后的 Cookie ，并暂时保存在 cookies 文件中。
2. 在`profile.json` 配置文件中编写数据库信息，爬虫启动时建立与数据库的连接。
3. 请求新片场广告页面的列表页，由于 11 ~ 15 页全部要求登录，因此请求在经过 Downloader Middleware 时被拦截，然后添加包含登录信息的 Cookie ，由此绕过登录反爬机制。
4. 获取到列表页响应后，构建 BS 对象，提取视频标题与详情页链接，接着通过详情页链接请求详情页数据，并把标题通过 meta 或者 cb_kwargs 一并传递过去。
5. 在详情页中通过 XPath 实现对点赞量、收藏量这两个数据的提取，然后从 URL 中提取出 Article ID 。（ Article ID 将作为三中数据类型的关联字段进行存储） 
6. 将 Article ID 、视频标题、点赞量、收藏量封装成一个 XpcBaseInfoItem 。
7. 根据规则拼出评论数据的 URL 地址，然后对其发起请求，并把 Article ID 通过 meta 或者 cb_kwargs 一并传递过去。
8. 评论数据响应的是一串 JSON 格式的数据，提取出其中的评论ID 、评论内容、评论时间，与 Article ID 一起封装一个 XpcCommentItem 。
9. 根据规则拼出视频播放地址数据的 URL 地址，然后对其发起请求，并把 Article ID 通过 meta 或者 cb_kwargs 一并传递过去。
10. 视频的 response 页是一个JSON格式的数据，直接用response.json()进行处理。 提取出其中的视频质量、视频地址，与 Article ID 一起封装一个 XpcVideoUrlItem 。
11. 当前页数据请求完毕后，判断下一页是否在目标区间内，若在则继续对下一页数据进行请求。
12. 对提取成功的数据进行存储，其中：
    - XpcBaseInfoItem 存储到 video_base_info 表中。（一个视频有一条数据）
    - XpcCommentItem 存储到 comment 表中。（一个视频有多条数据）
    - XpcVideoUrlItem 存储到 video_url 表中。（一个视频有多条数据）
13. 当所有数据都爬取完成后，删除 cookies 文件，并断开数据库连接。
