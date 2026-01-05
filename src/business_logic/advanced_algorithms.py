#!/usr/bin/env python3
"""
高级智能分析算法
实现情感关联分析、关键词共现分析、时间序列趋势分析、用户行为模式识别等高级算法

实现需求 13: 客户业务逻辑提炼与智能化 - 任务 47.1
"""

import logging
import numpy as np
import pandas as pd
from typing import List, Dict, Any, Tuple, Optional
from datetime import datetime, timedelta
from collections import defaultdict, Counter
from sklearn.feature_extraction.text import TfidfVectorizer, CountVectorizer
from sklearn.cluster import KMeans, DBSCAN
from sklearn.decomposition import PCA, LatentDirichletAllocation
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import StandardScaler
import networkx as nx
from scipy import stats
from scipy.stats import chi2_contingency
import spacy
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize, sent_tokenize
from nltk.stem import WordNetLemmatizer
from nltk.chunk import ne_chunk
from nltk.tag import pos_tag
import re

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 初始化NLP工具
try:
    # 尝试加载spaCy模型
    nlp = spacy.load("en_core_web_sm")
except OSError:
    logger.warning("spaCy英文模型未安装，使用基础功能")
    nlp = None

try:
    # 下载必要的NLTK数据
    nltk.download('punkt', quiet=True)
    nltk.download('stopwords', quiet=True)
    nltk.download('wordnet', quiet=True)
    nltk.download('averaged_perceptron_tagger', quiet=True)
    nltk.download('maxent_ne_chunker', quiet=True)
    nltk.download('words', quiet=True)
    
    # 初始化NLTK工具
    lemmatizer = WordNetLemmatizer()
    stop_words = set(stopwords.words('english'))
except Exception as e:
    logger.warning(f"NLTK初始化失败: {e}")
    lemmatizer = None
    stop_words = set()

class SentimentCorrelationAnalyzer:
    """情感关联分析器"""
    
    def __init__(self):
        self.vectorizer = TfidfVectorizer(
            max_features=1000,
            stop_words='english',
            ngram_range=(1, 3),
            min_df=2
        )
        
    def analyze_sentiment_keyword_correlation(self, annotations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        分析情感与关键词的关联性
        
        Args:
            annotations: 标注数据列表
            
        Returns:
            Dict: 关联分析结果
        """
        try:
            df = pd.DataFrame(annotations)
            
            if 'sentiment' not in df.columns or 'text' not in df.columns:
                return {"error": "缺少必要的字段"}
            
            # 按情感分组
            sentiment_groups = df.groupby('sentiment')
            correlations = {}
            
            for sentiment, group in sentiment_groups:
                texts = group['text'].fillna('').tolist()
                
                if len(texts) < 3:  # 数据太少
                    continue
                
                # 使用NLP增强的关键词提取
                keywords = self._extract_nlp_enhanced_keywords(texts)
                
                # 计算关键词权重
                keyword_weights = self._calculate_keyword_weights(texts, keywords)
                
                # 分析情感语义特征
                semantic_features = self._analyze_semantic_features(texts)
                
                correlations[sentiment] = {
                    "count": len(group),
                    "percentage": len(group) / len(df),
                    "top_keywords": keywords[:10],
                    "keyword_weights": keyword_weights,
                    "semantic_features": semantic_features,
                    "distinctive_score": self._calculate_distinctive_score(texts, df['text'].tolist())
                }
            
            # 计算情感间的相似度
            sentiment_similarity = self._calculate_sentiment_similarity(correlations)
            
            # 添加高级情感关联分析
            advanced_correlations = self._analyze_advanced_sentiment_correlations(df)
            
            return {
                "sentiment_correlations": correlations,
                "sentiment_similarity": sentiment_similarity,
                "advanced_correlations": advanced_correlations,
                "total_annotations": len(df),
                "analysis_timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"情感关联分析失败: {e}")
            return {"error": str(e)}
    
    def _extract_nlp_enhanced_keywords(self, texts: List[str]) -> List[str]:
        """使用NLP增强的关键词提取"""
        try:
            keywords = []
            
            # 方法1: 使用spaCy提取命名实体和重要词汇
            if nlp:
                all_entities = []
                important_tokens = []
                
                for text in texts:
                    doc = nlp(text)
                    
                    # 提取命名实体
                    entities = [ent.text.lower() for ent in doc.ents 
                              if ent.label_ in ['PERSON', 'ORG', 'PRODUCT', 'EVENT']]
                    all_entities.extend(entities)
                    
                    # 提取重要词汇 (名词、形容词、动词)
                    important = [token.lemma_.lower() for token in doc 
                               if (token.pos_ in ['NOUN', 'ADJ', 'VERB'] and 
                                   not token.is_stop and 
                                   not token.is_punct and 
                                   len(token.text) > 2)]
                    important_tokens.extend(important)
                
                # 统计频率
                entity_counts = Counter(all_entities)
                token_counts = Counter(important_tokens)
                
                # 合并结果
                keywords.extend([word for word, count in entity_counts.most_common(10) if count >= 2])
                keywords.extend([word for word, count in token_counts.most_common(15) if count >= 3])
            
            # 方法2: 使用NLTK进行词性标注和命名实体识别
            if lemmatizer and stop_words:
                nltk_keywords = []
                
                for text in texts:
                    # 分词和词性标注
                    tokens = word_tokenize(text.lower())
                    pos_tags = pos_tag(tokens)
                    
                    # 提取名词和形容词
                    important_words = [lemmatizer.lemmatize(word) for word, pos in pos_tags
                                     if (pos.startswith('NN') or pos.startswith('JJ')) and
                                        word not in stop_words and
                                        len(word) > 2 and
                                        word.isalpha()]
                    
                    nltk_keywords.extend(important_words)
                
                # 统计NLTK关键词
                nltk_counts = Counter(nltk_keywords)
                keywords.extend([word for word, count in nltk_counts.most_common(10) if count >= 2])
            
            # 方法3: 传统TF-IDF方法作为补充
            try:
                tfidf_matrix = self.vectorizer.fit_transform(texts)
                feature_names = self.vectorizer.get_feature_names_out()
                mean_scores = np.mean(tfidf_matrix.toarray(), axis=0)
                top_indices = np.argsort(mean_scores)[::-1][:15]
                tfidf_keywords = [feature_names[i] for i in top_indices if mean_scores[i] > 0.1]
                keywords.extend(tfidf_keywords)
            except Exception as e:
                logger.warning(f"TF-IDF关键词提取失败: {e}")
            
            # 去重并返回
            unique_keywords = list(dict.fromkeys(keywords))  # 保持顺序的去重
            return unique_keywords[:20]
            
        except Exception as e:
            logger.error(f"NLP增强关键词提取失败: {e}")
            return self._extract_sentiment_keywords(texts)  # 回退到原方法
    
    def _analyze_semantic_features(self, texts: List[str]) -> Dict[str, Any]:
        """分析语义特征"""
        try:
            features = {
                "average_sentence_length": 0,
                "average_word_length": 0,
                "pos_distribution": {},
                "named_entities": {},
                "sentiment_indicators": []
            }
            
            if not nlp:
                return features
            
            all_sentences = []
            all_words = []
            pos_counts = Counter()
            entity_counts = Counter()
            
            for text in texts:
                doc = nlp(text)
                
                # 句子长度
                sentences = [sent.text for sent in doc.sents]
                all_sentences.extend(sentences)
                
                # 词汇分析
                words = [token.text for token in doc if not token.is_punct]
                all_words.extend(words)
                
                # 词性分布
                pos_tags = [token.pos_ for token in doc if not token.is_punct]
                pos_counts.update(pos_tags)
                
                # 命名实体
                entities = [(ent.text, ent.label_) for ent in doc.ents]
                entity_counts.update([f"{ent[1]}:{ent[0]}" for ent in entities])
            
            # 计算特征
            if all_sentences:
                features["average_sentence_length"] = round(np.mean([len(s.split()) for s in all_sentences]), 2)
            
            if all_words:
                features["average_word_length"] = round(np.mean([len(w) for w in all_words]), 2)
            
            # 词性分布 (标准化)
            total_pos = sum(pos_counts.values())
            if total_pos > 0:
                features["pos_distribution"] = {
                    pos: round(count / total_pos, 3) 
                    for pos, count in pos_counts.most_common(10)
                }
            
            # 命名实体 (取前10个)
            features["named_entities"] = dict(entity_counts.most_common(10))
            
            return features
            
        except Exception as e:
            logger.error(f"语义特征分析失败: {e}")
            return {"error": str(e)}
    
    def _analyze_advanced_sentiment_correlations(self, df: pd.DataFrame) -> Dict[str, Any]:
        """高级情感关联分析"""
        try:
            advanced_analysis = {}
            
            # 1. 情感与文本长度的关联
            if 'text' in df.columns and 'sentiment' in df.columns:
                df['text_length'] = df['text'].str.len()
                length_sentiment = df.groupby('sentiment')['text_length'].agg(['mean', 'std']).round(2)
                advanced_analysis["length_sentiment_correlation"] = length_sentiment.to_dict()
            
            # 2. 情感与时间的关联 (如果有时间字段)
            if 'created_at' in df.columns and 'sentiment' in df.columns:
                df['created_at'] = pd.to_datetime(df['created_at'], errors='coerce')
                df['hour'] = df['created_at'].dt.hour
                
                # 按小时分析情感分布
                hourly_sentiment = df.groupby(['hour', 'sentiment']).size().unstack(fill_value=0)
                if not hourly_sentiment.empty:
                    # 计算每小时的主导情感
                    dominant_sentiment_by_hour = hourly_sentiment.idxmax(axis=1).to_dict()
                    advanced_analysis["hourly_sentiment_patterns"] = dominant_sentiment_by_hour
            
            # 3. 情感转换模式 (如果有用户和时间信息)
            if all(col in df.columns for col in ['annotator', 'created_at', 'sentiment']):
                df_sorted = df.sort_values(['annotator', 'created_at'])
                
                # 分析用户情感转换
                sentiment_transitions = {}
                for user, user_data in df_sorted.groupby('annotator'):
                    if len(user_data) > 1:
                        sentiments = user_data['sentiment'].tolist()
                        transitions = []
                        for i in range(len(sentiments) - 1):
                            transition = f"{sentiments[i]} -> {sentiments[i+1]}"
                            transitions.append(transition)
                        
                        if transitions:
                            transition_counts = Counter(transitions)
                            sentiment_transitions[user] = dict(transition_counts.most_common(5))
                
                advanced_analysis["sentiment_transition_patterns"] = sentiment_transitions
            
            return advanced_analysis
            
        except Exception as e:
            logger.error(f"高级情感关联分析失败: {e}")
            return {"error": str(e)}
    
    def _extract_sentiment_keywords(self, texts: List[str]) -> List[str]:
        """提取情感相关的关键词"""
        try:
            # 使用TF-IDF提取关键词
            tfidf_matrix = self.vectorizer.fit_transform(texts)
            feature_names = self.vectorizer.get_feature_names_out()
            
            # 计算平均TF-IDF分数
            mean_scores = np.mean(tfidf_matrix.toarray(), axis=0)
            
            # 获取top关键词
            top_indices = np.argsort(mean_scores)[::-1][:20]
            keywords = [feature_names[i] for i in top_indices if mean_scores[i] > 0.1]
            
            return keywords
            
        except Exception as e:
            logger.error(f"关键词提取失败: {e}")
            return []
    
    def _calculate_keyword_weights(self, texts: List[str], keywords: List[str]) -> Dict[str, float]:
        """计算关键词权重"""
        try:
            weights = {}
            total_texts = len(texts)
            
            for keyword in keywords:
                # 计算关键词在文本中的出现频率
                count = sum(1 for text in texts if keyword.lower() in text.lower())
                weight = count / total_texts
                weights[keyword] = round(weight, 3)
            
            return weights
            
        except Exception as e:
            logger.error(f"关键词权重计算失败: {e}")
            return {}
    
    def _calculate_distinctive_score(self, sentiment_texts: List[str], all_texts: List[str]) -> float:
        """计算情感的独特性分数"""
        try:
            # 计算该情感文本与全体文本的差异性
            sentiment_vocab = set()
            for text in sentiment_texts:
                words = re.findall(r'\b\w+\b', text.lower())
                sentiment_vocab.update(words)
            
            all_vocab = set()
            for text in all_texts:
                words = re.findall(r'\b\w+\b', text.lower())
                all_vocab.update(words)
            
            # 计算独特词汇比例
            unique_words = sentiment_vocab - all_vocab
            distinctive_score = len(unique_words) / len(sentiment_vocab) if sentiment_vocab else 0
            
            return round(distinctive_score, 3)
            
        except Exception as e:
            logger.error(f"独特性分数计算失败: {e}")
            return 0.0
    
    def _calculate_sentiment_similarity(self, correlations: Dict[str, Any]) -> Dict[str, float]:
        """计算情感间的相似度"""
        try:
            sentiments = list(correlations.keys())
            similarity_matrix = {}
            
            for i, sent1 in enumerate(sentiments):
                for j, sent2 in enumerate(sentiments):
                    if i >= j:
                        continue
                    
                    # 基于关键词计算相似度
                    keywords1 = set(correlations[sent1]["top_keywords"])
                    keywords2 = set(correlations[sent2]["top_keywords"])
                    
                    # Jaccard相似度
                    intersection = len(keywords1 & keywords2)
                    union = len(keywords1 | keywords2)
                    similarity = intersection / union if union > 0 else 0
                    
                    similarity_matrix[f"{sent1}-{sent2}"] = round(similarity, 3)
            
            return similarity_matrix
            
        except Exception as e:
            logger.error(f"情感相似度计算失败: {e}")
            return {}


class KeywordCooccurrenceAnalyzer:
    """关键词共现分析器"""
    
    def __init__(self, window_size: int = 5):
        self.window_size = window_size
        self.cooccurrence_matrix = None
        self.vocabulary = None
        
    def analyze_keyword_cooccurrence(self, annotations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        分析关键词共现模式
        
        Args:
            annotations: 标注数据列表
            
        Returns:
            Dict: 共现分析结果
        """
        try:
            df = pd.DataFrame(annotations)
            
            if 'text' not in df.columns:
                return {"error": "缺少文本字段"}
            
            texts = df['text'].fillna('').tolist()
            
            # 使用NLP增强的文本预处理
            processed_texts = self._preprocess_texts_with_nlp(texts)
            
            # 构建共现矩阵
            self._build_enhanced_cooccurrence_matrix(processed_texts)
            
            # 识别强共现关键词对
            strong_pairs = self._find_strong_cooccurrence_pairs()
            
            # 构建关键词网络
            keyword_network = self._build_keyword_network(strong_pairs)
            
            # 识别关键词社区
            communities = self._detect_keyword_communities(keyword_network)
            
            # 计算关键词中心性
            centrality_scores = self._calculate_keyword_centrality(keyword_network)
            
            # 语义关联分析
            semantic_associations = self._analyze_semantic_associations(processed_texts)
            
            return {
                "strong_cooccurrence_pairs": strong_pairs,
                "keyword_network": keyword_network,
                "keyword_communities": communities,
                "centrality_scores": centrality_scores,
                "semantic_associations": semantic_associations,
                "total_keywords": len(self.vocabulary) if self.vocabulary else 0,
                "analysis_timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"关键词共现分析失败: {e}")
            return {"error": str(e)}
    
    def _preprocess_texts_with_nlp(self, texts: List[str]) -> List[List[str]]:
        """使用NLP进行文本预处理"""
        try:
            processed_texts = []
            
            for text in texts:
                processed_words = []
                
                if nlp:
                    # 使用spaCy处理
                    doc = nlp(text)
                    for token in doc:
                        # 只保留有意义的词汇
                        if (not token.is_stop and 
                            not token.is_punct and 
                            not token.is_space and
                            len(token.text) > 2 and
                            token.pos_ in ['NOUN', 'ADJ', 'VERB', 'PROPN']):
                            processed_words.append(token.lemma_.lower())
                
                elif lemmatizer and stop_words:
                    # 使用NLTK处理
                    tokens = word_tokenize(text.lower())
                    pos_tags = pos_tag(tokens)
                    
                    for word, pos in pos_tags:
                        if (word not in stop_words and
                            len(word) > 2 and
                            word.isalpha() and
                            pos.startswith(('NN', 'JJ', 'VB'))):
                            lemmatized = lemmatizer.lemmatize(word)
                            processed_words.append(lemmatized)
                
                else:
                    # 基础处理
                    words = re.findall(r'\b\w+\b', text.lower())
                    processed_words = [w for w in words if len(w) > 2 and w not in self._get_stop_words()]
                
                processed_texts.append(processed_words)
            
            return processed_texts
            
        except Exception as e:
            logger.error(f"NLP文本预处理失败: {e}")
            # 回退到基础处理
            return [[w for w in re.findall(r'\b\w+\b', text.lower()) 
                    if len(w) > 2 and w not in self._get_stop_words()] 
                   for text in texts]
    
    def _build_enhanced_cooccurrence_matrix(self, processed_texts: List[List[str]]):
        """构建增强的共现矩阵"""
        try:
            # 收集所有词汇并计算频率
            all_words = []
            for words in processed_texts:
                all_words.extend(words)
            
            # 构建词汇表 (基于频率和重要性)
            word_counts = Counter(all_words)
            
            # 选择高频且有意义的词汇
            self.vocabulary = [word for word, count in word_counts.most_common(150) 
                             if count >= 3 and len(word) > 2]
            
            # 初始化共现矩阵
            vocab_size = len(self.vocabulary)
            self.cooccurrence_matrix = np.zeros((vocab_size, vocab_size))
            
            word_to_idx = {word: idx for idx, word in enumerate(self.vocabulary)}
            
            # 计算共现 (使用滑动窗口)
            for words in processed_texts:
                # 过滤词汇表中的词
                filtered_words = [w for w in words if w in word_to_idx]
                
                # 在窗口内计算共现
                for i, word1 in enumerate(filtered_words):
                    for j in range(max(0, i - self.window_size), 
                                 min(len(filtered_words), i + self.window_size + 1)):
                        if i != j:
                            word2 = filtered_words[j]
                            idx1, idx2 = word_to_idx[word1], word_to_idx[word2]
                            
                            # 考虑距离权重
                            distance = abs(i - j)
                            weight = 1.0 / distance if distance > 0 else 1.0
                            
                            self.cooccurrence_matrix[idx1][idx2] += weight
            
        except Exception as e:
            logger.error(f"增强共现矩阵构建失败: {e}")
    
    def _analyze_semantic_associations(self, processed_texts: List[List[str]]) -> Dict[str, Any]:
        """分析语义关联"""
        try:
            semantic_analysis = {}
            
            if not self.vocabulary:
                return semantic_analysis
            
            # 1. 主题聚类分析
            if len(processed_texts) >= 10:
                topic_clusters = self._perform_topic_clustering(processed_texts)
                semantic_analysis["topic_clusters"] = topic_clusters
            
            # 2. 语义相似度分析
            if nlp and len(self.vocabulary) >= 10:
                similarity_matrix = self._calculate_semantic_similarity()
                semantic_analysis["semantic_similarity"] = similarity_matrix
            
            # 3. 词汇语义角色分析
            semantic_roles = self._analyze_semantic_roles(processed_texts)
            semantic_analysis["semantic_roles"] = semantic_roles
            
            return semantic_analysis
            
        except Exception as e:
            logger.error(f"语义关联分析失败: {e}")
            return {"error": str(e)}
    
    def _perform_topic_clustering(self, processed_texts: List[List[str]]) -> Dict[str, Any]:
        """执行主题聚类"""
        try:
            # 将处理后的文本重新组合
            documents = [' '.join(words) for words in processed_texts]
            
            # 使用LDA进行主题建模
            vectorizer = CountVectorizer(max_features=100, min_df=2, max_df=0.8)
            doc_term_matrix = vectorizer.fit_transform(documents)
            
            # LDA主题建模
            n_topics = min(5, len(documents) // 3)  # 动态确定主题数
            if n_topics >= 2:
                lda = LatentDirichletAllocation(n_components=n_topics, random_state=42)
                lda.fit(doc_term_matrix)
                
                # 提取主题词汇
                feature_names = vectorizer.get_feature_names_out()
                topics = {}
                
                for topic_idx, topic in enumerate(lda.components_):
                    top_words_idx = topic.argsort()[-10:][::-1]
                    top_words = [feature_names[i] for i in top_words_idx]
                    topics[f"topic_{topic_idx}"] = {
                        "words": top_words,
                        "weights": [round(topic[i], 3) for i in top_words_idx]
                    }
                
                return {
                    "topics": topics,
                    "n_topics": n_topics,
                    "perplexity": round(lda.perplexity(doc_term_matrix), 2)
                }
            
            return {"error": "文档数量不足以进行主题聚类"}
            
        except Exception as e:
            logger.error(f"主题聚类失败: {e}")
            return {"error": str(e)}
    
    def _calculate_semantic_similarity(self) -> Dict[str, float]:
        """计算语义相似度"""
        try:
            if not nlp or len(self.vocabulary) < 5:
                return {}
            
            similarity_pairs = {}
            
            # 计算词汇间的语义相似度
            for i, word1 in enumerate(self.vocabulary[:20]):  # 限制计算量
                for j, word2 in enumerate(self.vocabulary[i+1:21], i+1):
                    try:
                        token1 = nlp(word1)
                        token2 = nlp(word2)
                        
                        if token1.has_vector and token2.has_vector:
                            similarity = token1.similarity(token2)
                            if similarity > 0.5:  # 只保留高相似度的词对
                                similarity_pairs[f"{word1}-{word2}"] = round(similarity, 3)
                    except Exception:
                        continue
            
            return similarity_pairs
            
        except Exception as e:
            logger.error(f"语义相似度计算失败: {e}")
            return {}
    
    def _analyze_semantic_roles(self, processed_texts: List[List[str]]) -> Dict[str, Any]:
        """分析语义角色"""
        try:
            if not self.vocabulary:
                return {}
            
            # 统计词汇在不同位置的出现频率
            position_stats = defaultdict(lambda: {"start": 0, "middle": 0, "end": 0})
            
            for words in processed_texts:
                if len(words) < 3:
                    continue
                
                for word in words:
                    if word in self.vocabulary:
                        # 确定词汇在句子中的位置
                        word_positions = [i for i, w in enumerate(words) if w == word]
                        
                        for pos in word_positions:
                            if pos < len(words) * 0.3:
                                position_stats[word]["start"] += 1
                            elif pos > len(words) * 0.7:
                                position_stats[word]["end"] += 1
                            else:
                                position_stats[word]["middle"] += 1
            
            # 分析语义角色
            semantic_roles = {
                "topic_introducers": [],  # 主题引入词
                "descriptors": [],        # 描述词
                "concluders": []          # 结论词
            }
            
            for word, stats in position_stats.items():
                total = sum(stats.values())
                if total >= 3:  # 至少出现3次
                    start_ratio = stats["start"] / total
                    end_ratio = stats["end"] / total
                    
                    if start_ratio > 0.5:
                        semantic_roles["topic_introducers"].append({
                            "word": word,
                            "start_ratio": round(start_ratio, 3)
                        })
                    elif end_ratio > 0.5:
                        semantic_roles["concluders"].append({
                            "word": word,
                            "end_ratio": round(end_ratio, 3)
                        })
                    else:
                        semantic_roles["descriptors"].append({
                            "word": word,
                            "middle_ratio": round(stats["middle"] / total, 3)
                        })
            
            # 按比例排序
            for role in semantic_roles:
                if role == "topic_introducers":
                    semantic_roles[role].sort(key=lambda x: x["start_ratio"], reverse=True)
                elif role == "concluders":
                    semantic_roles[role].sort(key=lambda x: x["end_ratio"], reverse=True)
                else:
                    semantic_roles[role].sort(key=lambda x: x["middle_ratio"], reverse=True)
                
                # 只保留前10个
                semantic_roles[role] = semantic_roles[role][:10]
            
            return semantic_roles
            
        except Exception as e:
            logger.error(f"语义角色分析失败: {e}")
            return {}
    
    def _build_cooccurrence_matrix(self, texts: List[str]):
        """构建共现矩阵"""
        try:
            # 提取所有关键词
            all_words = []
            for text in texts:
                words = re.findall(r'\b\w+\b', text.lower())
                # 过滤停用词和短词
                words = [w for w in words if len(w) > 2 and w not in self._get_stop_words()]
                all_words.extend(words)
            
            # 构建词汇表
            word_counts = Counter(all_words)
            self.vocabulary = [word for word, count in word_counts.most_common(100) if count >= 3]
            
            # 初始化共现矩阵
            vocab_size = len(self.vocabulary)
            self.cooccurrence_matrix = np.zeros((vocab_size, vocab_size))
            
            word_to_idx = {word: idx for idx, word in enumerate(self.vocabulary)}
            
            # 计算共现
            for text in texts:
                words = re.findall(r'\b\w+\b', text.lower())
                words = [w for w in words if w in word_to_idx]
                
                # 在窗口内计算共现
                for i, word1 in enumerate(words):
                    for j in range(max(0, i - self.window_size), min(len(words), i + self.window_size + 1)):
                        if i != j:
                            word2 = words[j]
                            idx1, idx2 = word_to_idx[word1], word_to_idx[word2]
                            self.cooccurrence_matrix[idx1][idx2] += 1
            
        except Exception as e:
            logger.error(f"共现矩阵构建失败: {e}")
    
    def _find_strong_cooccurrence_pairs(self, threshold: float = 0.1) -> List[Dict[str, Any]]:
        """识别强共现关键词对"""
        try:
            if self.cooccurrence_matrix is None or self.vocabulary is None:
                return []
            
            strong_pairs = []
            vocab_size = len(self.vocabulary)
            
            for i in range(vocab_size):
                for j in range(i + 1, vocab_size):
                    cooccurrence_count = self.cooccurrence_matrix[i][j] + self.cooccurrence_matrix[j][i]
                    
                    if cooccurrence_count > 0:
                        # 计算PMI (Pointwise Mutual Information)
                        word1_count = np.sum(self.cooccurrence_matrix[i, :])
                        word2_count = np.sum(self.cooccurrence_matrix[j, :])
                        total_pairs = np.sum(self.cooccurrence_matrix)
                        
                        if word1_count > 0 and word2_count > 0 and total_pairs > 0:
                            pmi = np.log2((cooccurrence_count * total_pairs) / (word1_count * word2_count))
                            
                            if pmi > threshold:
                                strong_pairs.append({
                                    "word1": self.vocabulary[i],
                                    "word2": self.vocabulary[j],
                                    "cooccurrence_count": int(cooccurrence_count),
                                    "pmi_score": round(pmi, 3)
                                })
            
            # 按PMI分数排序
            strong_pairs.sort(key=lambda x: x["pmi_score"], reverse=True)
            return strong_pairs[:50]  # 返回top 50
            
        except Exception as e:
            logger.error(f"强共现对识别失败: {e}")
            return []
    
    def _build_keyword_network(self, strong_pairs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """构建关键词网络"""
        try:
            G = nx.Graph()
            
            # 添加节点和边
            for pair in strong_pairs:
                word1, word2 = pair["word1"], pair["word2"]
                weight = pair["pmi_score"]
                
                G.add_node(word1)
                G.add_node(word2)
                G.add_edge(word1, word2, weight=weight)
            
            # 计算网络统计
            network_stats = {
                "nodes": G.number_of_nodes(),
                "edges": G.number_of_edges(),
                "density": nx.density(G),
                "average_clustering": nx.average_clustering(G) if G.number_of_nodes() > 0 else 0
            }
            
            # 转换为可序列化的格式
            nodes = [{"id": node, "degree": G.degree(node)} for node in G.nodes()]
            edges = [{"source": edge[0], "target": edge[1], "weight": G[edge[0]][edge[1]]["weight"]} 
                    for edge in G.edges()]
            
            return {
                "nodes": nodes,
                "edges": edges,
                "network_stats": network_stats
            }
            
        except Exception as e:
            logger.error(f"关键词网络构建失败: {e}")
            return {"nodes": [], "edges": [], "network_stats": {}}
    
    def _detect_keyword_communities(self, keyword_network: Dict[str, Any]) -> List[Dict[str, Any]]:
        """检测关键词社区"""
        try:
            if not keyword_network["edges"]:
                return []
            
            # 重建NetworkX图
            G = nx.Graph()
            for edge in keyword_network["edges"]:
                G.add_edge(edge["source"], edge["target"], weight=edge["weight"])
            
            # 使用Louvain算法检测社区
            try:
                import community as community_louvain
                partition = community_louvain.best_partition(G)
            except ImportError:
                # 如果没有community库，使用简单的连通分量
                partition = {}
                for i, component in enumerate(nx.connected_components(G)):
                    for node in component:
                        partition[node] = i
            
            # 组织社区结果
            communities = defaultdict(list)
            for node, community_id in partition.items():
                communities[community_id].append(node)
            
            community_list = []
            for community_id, members in communities.items():
                if len(members) >= 2:  # 至少2个成员才算社区
                    community_list.append({
                        "community_id": community_id,
                        "members": members,
                        "size": len(members)
                    })
            
            return community_list
            
        except Exception as e:
            logger.error(f"关键词社区检测失败: {e}")
            return []
    
    def _calculate_keyword_centrality(self, keyword_network: Dict[str, Any]) -> Dict[str, float]:
        """计算关键词中心性"""
        try:
            if not keyword_network["edges"]:
                return {}
            
            # 重建NetworkX图
            G = nx.Graph()
            for edge in keyword_network["edges"]:
                G.add_edge(edge["source"], edge["target"], weight=edge["weight"])
            
            # 计算不同类型的中心性
            degree_centrality = nx.degree_centrality(G)
            betweenness_centrality = nx.betweenness_centrality(G)
            closeness_centrality = nx.closeness_centrality(G)
            
            # 综合中心性分数
            centrality_scores = {}
            for node in G.nodes():
                combined_score = (
                    degree_centrality.get(node, 0) * 0.4 +
                    betweenness_centrality.get(node, 0) * 0.3 +
                    closeness_centrality.get(node, 0) * 0.3
                )
                centrality_scores[node] = round(combined_score, 3)
            
            return centrality_scores
            
        except Exception as e:
            logger.error(f"关键词中心性计算失败: {e}")
            return {}
    
    def _get_stop_words(self) -> set:
        """获取停用词列表"""
        return {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by',
            'is', 'are', 'was', 'were', 'be', 'been', 'have', 'has', 'had', 'do', 'does', 'did',
            'will', 'would', 'could', 'should', 'may', 'might', 'can', 'this', 'that', 'these', 'those'
        }


class TimeSeriesTrendAnalyzer:
    """时间序列趋势分析器"""
    
    def __init__(self):
        self.scaler = StandardScaler()
        
    def analyze_temporal_trends(self, annotations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        分析时间序列趋势
        
        Args:
            annotations: 标注数据列表
            
        Returns:
            Dict: 趋势分析结果
        """
        try:
            df = pd.DataFrame(annotations)
            
            if 'created_at' not in df.columns:
                return {"error": "缺少时间字段"}
            
            # 转换时间字段
            df['created_at'] = pd.to_datetime(df['created_at'], errors='coerce')
            df = df.dropna(subset=['created_at'])
            
            if len(df) < 10:
                return {"error": "数据量不足"}
            
            # 按日期聚合
            daily_stats = self._calculate_daily_statistics(df)
            
            # 趋势检测
            trends = self._detect_trends(daily_stats)
            
            # 季节性分析
            seasonality = self._analyze_seasonality(daily_stats)
            
            # 异常检测
            anomalies = self._detect_anomalies(daily_stats)
            
            # 预测未来趋势
            predictions = self._predict_future_trends(daily_stats)
            
            return {
                "daily_statistics": daily_stats,
                "trend_analysis": trends,
                "seasonality_analysis": seasonality,
                "anomaly_detection": anomalies,
                "future_predictions": predictions,
                "analysis_period": {
                    "start_date": df['created_at'].min().isoformat(),
                    "end_date": df['created_at'].max().isoformat(),
                    "total_days": (df['created_at'].max() - df['created_at'].min()).days
                },
                "analysis_timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"时间序列趋势分析失败: {e}")
            return {"error": str(e)}
    
    def _calculate_daily_statistics(self, df: pd.DataFrame) -> Dict[str, Any]:
        """计算每日统计数据"""
        try:
            # 按日期分组
            daily_groups = df.groupby(df['created_at'].dt.date)
            
            daily_stats = []
            for date, group in daily_groups:
                stats = {
                    "date": date.isoformat(),
                    "annotation_count": len(group),
                    "unique_annotators": group['annotator'].nunique() if 'annotator' in group.columns else 0,
                }
                
                # 情感分布统计
                if 'sentiment' in group.columns:
                    sentiment_dist = group['sentiment'].value_counts().to_dict()
                    stats["sentiment_distribution"] = sentiment_dist
                    
                    # 计算情感多样性 (Shannon熵)
                    sentiment_counts = list(sentiment_dist.values())
                    total = sum(sentiment_counts)
                    if total > 0:
                        probs = [count / total for count in sentiment_counts]
                        entropy = -sum(p * np.log2(p) for p in probs if p > 0)
                        stats["sentiment_diversity"] = round(entropy, 3)
                
                # 评分统计
                if 'rating' in group.columns:
                    ratings = group['rating'].dropna()
                    if len(ratings) > 0:
                        stats["average_rating"] = round(ratings.mean(), 2)
                        stats["rating_std"] = round(ratings.std(), 2)
                
                daily_stats.append(stats)
            
            return {
                "daily_data": daily_stats,
                "total_days": len(daily_stats),
                "date_range": {
                    "start": daily_stats[0]["date"] if daily_stats else None,
                    "end": daily_stats[-1]["date"] if daily_stats else None
                }
            }
            
        except Exception as e:
            logger.error(f"每日统计计算失败: {e}")
            return {"daily_data": [], "total_days": 0}
    
    def _detect_trends(self, daily_stats: Dict[str, Any]) -> Dict[str, Any]:
        """检测趋势"""
        try:
            daily_data = daily_stats["daily_data"]
            if len(daily_data) < 7:
                return {"error": "数据不足以进行趋势分析"}
            
            # 提取数值序列
            annotation_counts = [day["annotation_count"] for day in daily_data]
            dates = [datetime.fromisoformat(day["date"]) for day in daily_data]
            
            # 线性趋势检测
            x = np.arange(len(annotation_counts))
            slope, intercept, r_value, p_value, std_err = stats.linregress(x, annotation_counts)
            
            # 趋势强度和方向
            trend_strength = abs(r_value)
            trend_direction = "increasing" if slope > 0 else "decreasing" if slope < 0 else "stable"
            
            # 移动平均趋势
            window_size = min(7, len(annotation_counts) // 3)
            if window_size >= 3:
                moving_avg = pd.Series(annotation_counts).rolling(window=window_size).mean().tolist()
                moving_avg_trend = self._calculate_moving_average_trend(moving_avg)
            else:
                moving_avg = []
                moving_avg_trend = {}
            
            return {
                "linear_trend": {
                    "slope": round(slope, 4),
                    "r_squared": round(r_value ** 2, 4),
                    "p_value": round(p_value, 4),
                    "direction": trend_direction,
                    "strength": round(trend_strength, 3),
                    "significance": "significant" if p_value < 0.05 else "not_significant"
                },
                "moving_average_trend": moving_avg_trend,
                "trend_summary": {
                    "overall_direction": trend_direction,
                    "confidence": round(trend_strength, 3),
                    "is_significant": p_value < 0.05
                }
            }
            
        except Exception as e:
            logger.error(f"趋势检测失败: {e}")
            return {"error": str(e)}
    
    def _calculate_moving_average_trend(self, moving_avg: List[float]) -> Dict[str, Any]:
        """计算移动平均趋势"""
        try:
            # 过滤NaN值
            valid_values = [v for v in moving_avg if not pd.isna(v)]
            
            if len(valid_values) < 3:
                return {"error": "移动平均数据不足"}
            
            # 计算变化率
            changes = []
            for i in range(1, len(valid_values)):
                change_rate = (valid_values[i] - valid_values[i-1]) / valid_values[i-1] if valid_values[i-1] != 0 else 0
                changes.append(change_rate)
            
            avg_change_rate = np.mean(changes) if changes else 0
            
            return {
                "average_change_rate": round(avg_change_rate, 4),
                "trend_direction": "increasing" if avg_change_rate > 0.01 else "decreasing" if avg_change_rate < -0.01 else "stable",
                "volatility": round(np.std(changes), 4) if changes else 0
            }
            
        except Exception as e:
            logger.error(f"移动平均趋势计算失败: {e}")
            return {"error": str(e)}
    
    def _analyze_seasonality(self, daily_stats: Dict[str, Any]) -> Dict[str, Any]:
        """分析季节性模式"""
        try:
            daily_data = daily_stats["daily_data"]
            if len(daily_data) < 14:
                return {"error": "数据不足以进行季节性分析"}
            
            # 按星期几分组
            weekday_stats = defaultdict(list)
            for day in daily_data:
                date = datetime.fromisoformat(day["date"])
                weekday = date.weekday()  # 0=Monday, 6=Sunday
                weekday_stats[weekday].append(day["annotation_count"])
            
            # 计算每个星期几的平均值
            weekday_averages = {}
            weekday_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
            
            for weekday, counts in weekday_stats.items():
                if counts:
                    weekday_averages[weekday_names[weekday]] = {
                        "average": round(np.mean(counts), 2),
                        "std": round(np.std(counts), 2),
                        "count": len(counts)
                    }
            
            # 检测周末效应
            weekday_counts = []
            weekend_counts = []
            
            for weekday, counts in weekday_stats.items():
                if weekday < 5:  # Monday-Friday
                    weekday_counts.extend(counts)
                else:  # Saturday-Sunday
                    weekend_counts.extend(counts)
            
            weekend_effect = {}
            if weekday_counts and weekend_counts:
                weekday_avg = np.mean(weekday_counts)
                weekend_avg = np.mean(weekend_counts)
                
                # 进行t检验
                if len(weekday_counts) > 1 and len(weekend_counts) > 1:
                    t_stat, p_value = stats.ttest_ind(weekday_counts, weekend_counts)
                    weekend_effect = {
                        "weekday_average": round(weekday_avg, 2),
                        "weekend_average": round(weekend_avg, 2),
                        "difference": round(weekend_avg - weekday_avg, 2),
                        "t_statistic": round(t_stat, 4),
                        "p_value": round(p_value, 4),
                        "significant": p_value < 0.05
                    }
            
            return {
                "weekday_patterns": weekday_averages,
                "weekend_effect": weekend_effect,
                "seasonality_detected": len(weekday_averages) >= 7
            }
            
        except Exception as e:
            logger.error(f"季节性分析失败: {e}")
            return {"error": str(e)}
    
    def _detect_anomalies(self, daily_stats: Dict[str, Any]) -> Dict[str, Any]:
        """检测异常值"""
        try:
            daily_data = daily_stats["daily_data"]
            if len(daily_data) < 10:
                return {"error": "数据不足以进行异常检测"}
            
            annotation_counts = [day["annotation_count"] for day in daily_data]
            
            # 使用IQR方法检测异常值
            Q1 = np.percentile(annotation_counts, 25)
            Q3 = np.percentile(annotation_counts, 75)
            IQR = Q3 - Q1
            
            lower_bound = Q1 - 1.5 * IQR
            upper_bound = Q3 + 1.5 * IQR
            
            anomalies = []
            for i, day in enumerate(daily_data):
                count = day["annotation_count"]
                if count < lower_bound or count > upper_bound:
                    anomaly_type = "low" if count < lower_bound else "high"
                    severity = abs(count - np.median(annotation_counts)) / np.std(annotation_counts)
                    
                    anomalies.append({
                        "date": day["date"],
                        "value": count,
                        "type": anomaly_type,
                        "severity": round(severity, 2),
                        "expected_range": [round(lower_bound, 1), round(upper_bound, 1)]
                    })
            
            # 统计信息
            anomaly_stats = {
                "total_anomalies": len(anomalies),
                "anomaly_rate": round(len(anomalies) / len(daily_data), 3),
                "high_anomalies": len([a for a in anomalies if a["type"] == "high"]),
                "low_anomalies": len([a for a in anomalies if a["type"] == "low"])
            }
            
            return {
                "anomalies": anomalies,
                "anomaly_statistics": anomaly_stats,
                "detection_parameters": {
                    "method": "IQR",
                    "lower_bound": round(lower_bound, 2),
                    "upper_bound": round(upper_bound, 2),
                    "Q1": round(Q1, 2),
                    "Q3": round(Q3, 2),
                    "IQR": round(IQR, 2)
                }
            }
            
        except Exception as e:
            logger.error(f"异常检测失败: {e}")
            return {"error": str(e)}
    
    def _predict_future_trends(self, daily_stats: Dict[str, Any], forecast_days: int = 7) -> Dict[str, Any]:
        """预测未来趋势"""
        try:
            daily_data = daily_stats["daily_data"]
            if len(daily_data) < 14:
                return {"error": "历史数据不足以进行预测"}
            
            annotation_counts = [day["annotation_count"] for day in daily_data]
            
            # 简单线性回归预测
            x = np.arange(len(annotation_counts))
            slope, intercept, r_value, p_value, std_err = stats.linregress(x, annotation_counts)
            
            # 生成未来预测
            future_x = np.arange(len(annotation_counts), len(annotation_counts) + forecast_days)
            future_predictions = slope * future_x + intercept
            
            # 计算预测区间
            residuals = np.array(annotation_counts) - (slope * x + intercept)
            mse = np.mean(residuals ** 2)
            prediction_std = np.sqrt(mse)
            
            predictions = []
            last_date = datetime.fromisoformat(daily_data[-1]["date"])
            
            for i, pred_value in enumerate(future_predictions):
                pred_date = last_date + timedelta(days=i + 1)
                
                # 确保预测值不为负
                pred_value = max(0, pred_value)
                lower_bound = max(0, pred_value - 1.96 * prediction_std)
                upper_bound = pred_value + 1.96 * prediction_std
                
                predictions.append({
                    "date": pred_date.date().isoformat(),
                    "predicted_value": round(pred_value, 1),
                    "confidence_interval": {
                        "lower": round(lower_bound, 1),
                        "upper": round(upper_bound, 1)
                    },
                    "confidence_level": 0.95
                })
            
            return {
                "predictions": predictions,
                "model_performance": {
                    "r_squared": round(r_value ** 2, 4),
                    "mean_squared_error": round(mse, 4),
                    "prediction_std": round(prediction_std, 4)
                },
                "forecast_summary": {
                    "forecast_days": forecast_days,
                    "trend_direction": "increasing" if slope > 0 else "decreasing" if slope < 0 else "stable",
                    "average_daily_change": round(slope, 2)
                }
            }
            
        except Exception as e:
            logger.error(f"未来趋势预测失败: {e}")
            return {"error": str(e)}


class UserBehaviorPatternAnalyzer:
    """用户行为模式识别器"""
    
    def __init__(self):
        self.clustering_model = None
        
    def analyze_user_behavior_patterns(self, annotations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        分析用户行为模式
        
        Args:
            annotations: 标注数据列表
            
        Returns:
            Dict: 用户行为分析结果
        """
        try:
            df = pd.DataFrame(annotations)
            
            if 'annotator' not in df.columns:
                return {"error": "缺少标注者字段"}
            
            # 用户活动统计
            user_activity = self._analyze_user_activity(df)
            
            # 用户行为聚类
            user_clusters = self._cluster_user_behavior(df)
            
            # 协作模式分析
            collaboration_patterns = self._analyze_collaboration_patterns(df)
            
            # 质量模式分析
            quality_patterns = self._analyze_quality_patterns(df)
            
            # 时间模式分析
            temporal_patterns = self._analyze_temporal_patterns(df)
            
            return {
                "user_activity_analysis": user_activity,
                "user_behavior_clusters": user_clusters,
                "collaboration_patterns": collaboration_patterns,
                "quality_patterns": quality_patterns,
                "temporal_patterns": temporal_patterns,
                "total_users": df['annotator'].nunique(),
                "total_annotations": len(df),
                "analysis_timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"用户行为模式分析失败: {e}")
            return {"error": str(e)}
    
    def _analyze_user_activity(self, df: pd.DataFrame) -> Dict[str, Any]:
        """分析用户活动模式"""
        try:
            user_stats = []
            
            for user, user_data in df.groupby('annotator'):
                stats = {
                    "user_id": user,
                    "total_annotations": len(user_data),
                    "activity_span_days": 0,
                    "average_daily_annotations": 0,
                    "consistency_score": 0
                }
                
                # 时间跨度分析
                if 'created_at' in user_data.columns:
                    user_data['created_at'] = pd.to_datetime(user_data['created_at'], errors='coerce')
                    valid_dates = user_data['created_at'].dropna()
                    
                    if len(valid_dates) > 0:
                        date_range = (valid_dates.max() - valid_dates.min()).days + 1
                        stats["activity_span_days"] = date_range
                        stats["average_daily_annotations"] = round(len(user_data) / date_range, 2)
                        
                        # 一致性分数 (基于标注分布的均匀程度)
                        daily_counts = valid_dates.dt.date.value_counts()
                        if len(daily_counts) > 1:
                            cv = daily_counts.std() / daily_counts.mean()  # 变异系数
                            stats["consistency_score"] = round(1 / (1 + cv), 3)  # 转换为0-1分数
                
                # 情感分布分析
                if 'sentiment' in user_data.columns:
                    sentiment_dist = user_data['sentiment'].value_counts(normalize=True).to_dict()
                    stats["sentiment_distribution"] = {k: round(v, 3) for k, v in sentiment_dist.items()}
                
                # 评分模式分析
                if 'rating' in user_data.columns:
                    ratings = user_data['rating'].dropna()
                    if len(ratings) > 0:
                        stats["rating_patterns"] = {
                            "average_rating": round(ratings.mean(), 2),
                            "rating_std": round(ratings.std(), 2),
                            "rating_range": [int(ratings.min()), int(ratings.max())],
                            "most_common_rating": int(ratings.mode().iloc[0]) if len(ratings.mode()) > 0 else None
                        }
                
                user_stats.append(stats)
            
            # 用户分类
            user_categories = self._categorize_users(user_stats)
            
            return {
                "individual_user_stats": user_stats,
                "user_categories": user_categories,
                "activity_summary": {
                    "most_active_user": max(user_stats, key=lambda x: x["total_annotations"])["user_id"],
                    "average_annotations_per_user": round(np.mean([u["total_annotations"] for u in user_stats]), 2),
                    "user_activity_distribution": self._calculate_activity_distribution(user_stats)
                }
            }
            
        except Exception as e:
            logger.error(f"用户活动分析失败: {e}")
            return {"error": str(e)}
    
    def _categorize_users(self, user_stats: List[Dict[str, Any]]) -> Dict[str, List[str]]:
        """用户分类"""
        try:
            categories = {
                "high_volume": [],      # 高产量用户
                "consistent": [],       # 一致性用户
                "occasional": [],       # 偶尔用户
                "new": []              # 新用户
            }
            
            if not user_stats:
                return categories
            
            # 计算阈值
            annotation_counts = [u["total_annotations"] for u in user_stats]
            consistency_scores = [u.get("consistency_score", 0) for u in user_stats]
            activity_spans = [u.get("activity_span_days", 0) for u in user_stats]
            
            high_volume_threshold = np.percentile(annotation_counts, 75)
            high_consistency_threshold = np.percentile(consistency_scores, 75)
            
            for user in user_stats:
                user_id = user["user_id"]
                
                # 高产量用户
                if user["total_annotations"] >= high_volume_threshold:
                    categories["high_volume"].append(user_id)
                
                # 一致性用户
                if user.get("consistency_score", 0) >= high_consistency_threshold:
                    categories["consistent"].append(user_id)
                
                # 新用户 (活动时间少于7天)
                if user.get("activity_span_days", 0) <= 7:
                    categories["new"].append(user_id)
                
                # 偶尔用户 (标注量少且活动时间长)
                if (user["total_annotations"] < high_volume_threshold / 2 and 
                    user.get("activity_span_days", 0) > 14):
                    categories["occasional"].append(user_id)
            
            return categories
            
        except Exception as e:
            logger.error(f"用户分类失败: {e}")
            return {"high_volume": [], "consistent": [], "occasional": [], "new": []}
    
    def _calculate_activity_distribution(self, user_stats: List[Dict[str, Any]]) -> Dict[str, int]:
        """计算活动分布"""
        try:
            distribution = {"1-10": 0, "11-50": 0, "51-100": 0, "100+": 0}
            
            for user in user_stats:
                count = user["total_annotations"]
                if count <= 10:
                    distribution["1-10"] += 1
                elif count <= 50:
                    distribution["11-50"] += 1
                elif count <= 100:
                    distribution["51-100"] += 1
                else:
                    distribution["100+"] += 1
            
            return distribution
            
        except Exception as e:
            logger.error(f"活动分布计算失败: {e}")
            return {"1-10": 0, "11-50": 0, "51-100": 0, "100+": 0}
    
    def _cluster_user_behavior(self, df: pd.DataFrame) -> Dict[str, Any]:
        """用户行为聚类"""
        try:
            # 构建用户特征矩阵
            user_features = []
            user_ids = []
            
            for user, user_data in df.groupby('annotator'):
                features = []
                
                # 基本活动特征
                features.append(len(user_data))  # 标注总数
                
                # 时间特征
                if 'created_at' in user_data.columns:
                    user_data['created_at'] = pd.to_datetime(user_data['created_at'], errors='coerce')
                    valid_dates = user_data['created_at'].dropna()
                    
                    if len(valid_dates) > 0:
                        activity_span = (valid_dates.max() - valid_dates.min()).days + 1
                        features.append(activity_span)
                        features.append(len(user_data) / activity_span)  # 日均标注数
                    else:
                        features.extend([0, 0])
                else:
                    features.extend([0, 0])
                
                # 情感分布特征
                if 'sentiment' in user_data.columns:
                    sentiment_counts = user_data['sentiment'].value_counts()
                    total = len(user_data)
                    
                    # 各情感比例
                    for sentiment in ['positive', 'negative', 'neutral']:
                        ratio = sentiment_counts.get(sentiment, 0) / total
                        features.append(ratio)
                else:
                    features.extend([0, 0, 0])
                
                # 评分特征
                if 'rating' in user_data.columns:
                    ratings = user_data['rating'].dropna()
                    if len(ratings) > 0:
                        features.append(ratings.mean())
                        features.append(ratings.std())
                    else:
                        features.extend([0, 0])
                else:
                    features.extend([0, 0])
                
                user_features.append(features)
                user_ids.append(user)
            
            if len(user_features) < 3:
                return {"error": "用户数量不足以进行聚类"}
            
            # 标准化特征
            features_array = np.array(user_features)
            features_scaled = self.scaler.fit_transform(features_array)
            
            # K-means聚类
            optimal_k = min(4, len(user_features) // 2)  # 最多4个聚类
            if optimal_k >= 2:
                kmeans = KMeans(n_clusters=optimal_k, random_state=42, n_init=10)
                cluster_labels = kmeans.fit_predict(features_scaled)
                
                # 组织聚类结果
                clusters = defaultdict(list)
                for user_id, cluster_id in zip(user_ids, cluster_labels):
                    clusters[int(cluster_id)].append(user_id)
                
                # 计算聚类中心特征
                cluster_centers = {}
                feature_names = [
                    "total_annotations", "activity_span", "daily_avg",
                    "positive_ratio", "negative_ratio", "neutral_ratio",
                    "avg_rating", "rating_std"
                ]
                
                for i, center in enumerate(kmeans.cluster_centers_):
                    # 反标准化
                    original_center = self.scaler.inverse_transform([center])[0]
                    cluster_centers[i] = {
                        name: round(float(value), 3) 
                        for name, value in zip(feature_names, original_center)
                    }
                
                return {
                    "clusters": dict(clusters),
                    "cluster_centers": cluster_centers,
                    "cluster_count": optimal_k,
                    "clustering_method": "K-means"
                }
            else:
                return {"error": "用户数量不足以进行有效聚类"}
            
        except Exception as e:
            logger.error(f"用户行为聚类失败: {e}")
            return {"error": str(e)}
    
    def _analyze_collaboration_patterns(self, df: pd.DataFrame) -> Dict[str, Any]:
        """分析协作模式"""
        try:
            collaboration_stats = {}
            
            # 如果有任务ID，分析多人标注同一任务的情况
            if 'task_id' in df.columns:
                task_annotators = df.groupby('task_id')['annotator'].nunique()
                multi_annotator_tasks = task_annotators[task_annotators > 1]
                
                collaboration_stats["multi_annotator_tasks"] = {
                    "count": len(multi_annotator_tasks),
                    "percentage": round(len(multi_annotator_tasks) / len(task_annotators) * 100, 2),
                    "average_annotators_per_task": round(multi_annotator_tasks.mean(), 2)
                }
                
                # 分析标注一致性
                if len(multi_annotator_tasks) > 0:
                    consistency_scores = []
                    for task_id in multi_annotator_tasks.index:
                        task_data = df[df['task_id'] == task_id]
                        if 'sentiment' in task_data.columns:
                            # 计算情感标注一致性
                            sentiment_agreement = len(task_data['sentiment'].unique()) == 1
                            consistency_scores.append(1.0 if sentiment_agreement else 0.0)
                    
                    if consistency_scores:
                        collaboration_stats["annotation_consistency"] = {
                            "average_agreement": round(np.mean(consistency_scores), 3),
                            "total_compared_tasks": len(consistency_scores)
                        }
            
            # 分析用户间的协作频率
            if 'created_at' in df.columns:
                df['created_at'] = pd.to_datetime(df['created_at'], errors='coerce')
                df['date'] = df['created_at'].dt.date
                
                # 按日期分组，看每天有多少用户协作
                daily_collaboration = df.groupby('date')['annotator'].nunique()
                
                collaboration_stats["daily_collaboration"] = {
                    "average_users_per_day": round(daily_collaboration.mean(), 2),
                    "max_users_per_day": int(daily_collaboration.max()),
                    "days_with_multiple_users": int((daily_collaboration > 1).sum()),
                    "total_active_days": len(daily_collaboration)
                }
            
            return collaboration_stats
            
        except Exception as e:
            logger.error(f"协作模式分析失败: {e}")
            return {"error": str(e)}
    
    def _analyze_quality_patterns(self, df: pd.DataFrame) -> Dict[str, Any]:
        """分析质量模式"""
        try:
            quality_patterns = {}
            
            # 用户质量分析
            user_quality = []
            
            for user, user_data in df.groupby('annotator'):
                quality_metrics = {"user_id": user}
                
                # 评分质量分析
                if 'rating' in user_data.columns:
                    ratings = user_data['rating'].dropna()
                    if len(ratings) > 0:
                        # 评分分布的熵 (多样性)
                        rating_counts = ratings.value_counts(normalize=True)
                        entropy = -sum(p * np.log2(p) for p in rating_counts if p > 0)
                        
                        quality_metrics["rating_diversity"] = round(entropy, 3)
                        quality_metrics["rating_consistency"] = round(1 - ratings.std() / 5, 3)  # 标准化一致性
                
                # 情感标注质量
                if 'sentiment' in user_data.columns:
                    sentiment_counts = user_data['sentiment'].value_counts(normalize=True)
                    sentiment_entropy = -sum(p * np.log2(p) for p in sentiment_counts if p > 0)
                    
                    quality_metrics["sentiment_diversity"] = round(sentiment_entropy, 3)
                
                # 标注速度分析 (如果有时间戳)
                if 'created_at' in user_data.columns and len(user_data) > 1:
                    user_data_sorted = user_data.sort_values('created_at')
                    time_diffs = user_data_sorted['created_at'].diff().dt.total_seconds().dropna()
                    
                    if len(time_diffs) > 0:
                        avg_time_between = time_diffs.mean()
                        quality_metrics["average_annotation_interval"] = round(avg_time_between, 2)
                        quality_metrics["annotation_speed_consistency"] = round(1 - time_diffs.std() / time_diffs.mean(), 3)
                
                user_quality.append(quality_metrics)
            
            quality_patterns["user_quality_metrics"] = user_quality
            
            # 整体质量趋势
            if 'created_at' in df.columns:
                df['created_at'] = pd.to_datetime(df['created_at'], errors='coerce')
                df_sorted = df.sort_values('created_at')
                
                # 按时间窗口分析质量变化
                if 'rating' in df.columns:
                    # 使用滑动窗口计算质量趋势
                    window_size = max(10, len(df) // 10)
                    quality_trend = df_sorted['rating'].rolling(window=window_size).mean()
                    
                    quality_patterns["quality_trend"] = {
                        "trend_direction": "improving" if quality_trend.iloc[-1] > quality_trend.iloc[0] else "declining",
                        "trend_strength": round(abs(quality_trend.iloc[-1] - quality_trend.iloc[0]), 3),
                        "average_quality": round(df['rating'].mean(), 2)
                    }
            
            return quality_patterns
            
        except Exception as e:
            logger.error(f"质量模式分析失败: {e}")
            return {"error": str(e)}
    
    def _analyze_temporal_patterns(self, df: pd.DataFrame) -> Dict[str, Any]:
        """分析时间模式"""
        try:
            if 'created_at' not in df.columns:
                return {"error": "缺少时间字段"}
            
            df['created_at'] = pd.to_datetime(df['created_at'], errors='coerce')
            df = df.dropna(subset=['created_at'])
            
            if len(df) == 0:
                return {"error": "没有有效的时间数据"}
            
            temporal_patterns = {}
            
            # 按小时分析
            df['hour'] = df['created_at'].dt.hour
            hourly_activity = df['hour'].value_counts().sort_index()
            
            temporal_patterns["hourly_patterns"] = {
                "peak_hours": hourly_activity.nlargest(3).index.tolist(),
                "low_activity_hours": hourly_activity.nsmallest(3).index.tolist(),
                "hourly_distribution": hourly_activity.to_dict()
            }
            
            # 按星期几分析
            df['weekday'] = df['created_at'].dt.day_name()
            weekday_activity = df['weekday'].value_counts()
            
            temporal_patterns["weekday_patterns"] = {
                "most_active_days": weekday_activity.nlargest(3).index.tolist(),
                "least_active_days": weekday_activity.nsmallest(3).index.tolist(),
                "weekday_distribution": weekday_activity.to_dict()
            }
            
            # 用户个人时间偏好
            user_time_preferences = {}
            for user, user_data in df.groupby('annotator'):
                if len(user_data) >= 5:  # 至少5个标注才分析
                    user_hours = user_data['hour'].value_counts()
                    preferred_hours = user_hours.nlargest(3).index.tolist()
                    
                    user_time_preferences[user] = {
                        "preferred_hours": preferred_hours,
                        "activity_span": {
                            "earliest": int(user_data['hour'].min()),
                            "latest": int(user_data['hour'].max())
                        }
                    }
            
            temporal_patterns["user_time_preferences"] = user_time_preferences
            
            return temporal_patterns
            
        except Exception as e:
            logger.error(f"时间模式分析失败: {e}")
            return {"error": str(e)}


# 主要的高级算法管理器
class AdvancedAlgorithmManager:
    """高级算法管理器"""
    
    def __init__(self):
        self.sentiment_analyzer = SentimentCorrelationAnalyzer()
        self.keyword_analyzer = KeywordCooccurrenceAnalyzer()
        self.trend_analyzer = TimeSeriesTrendAnalyzer()
        self.behavior_analyzer = UserBehaviorPatternAnalyzer()
    
    def run_comprehensive_analysis(self, annotations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        运行综合分析
        
        Args:
            annotations: 标注数据列表
            
        Returns:
            Dict: 综合分析结果
        """
        logger.info("开始运行高级智能分析算法")
        
        results = {
            "analysis_timestamp": datetime.now().isoformat(),
            "total_annotations": len(annotations),
            "algorithms_used": []
        }
        
        # 1. 情感关联分析
        try:
            sentiment_results = self.sentiment_analyzer.analyze_sentiment_keyword_correlation(annotations)
            results["sentiment_correlation_analysis"] = sentiment_results
            results["algorithms_used"].append("sentiment_correlation")
            logger.info("✅ 情感关联分析完成")
        except Exception as e:
            logger.error(f"❌ 情感关联分析失败: {e}")
            results["sentiment_correlation_analysis"] = {"error": str(e)}
        
        # 2. 关键词共现分析
        try:
            keyword_results = self.keyword_analyzer.analyze_keyword_cooccurrence(annotations)
            results["keyword_cooccurrence_analysis"] = keyword_results
            results["algorithms_used"].append("keyword_cooccurrence")
            logger.info("✅ 关键词共现分析完成")
        except Exception as e:
            logger.error(f"❌ 关键词共现分析失败: {e}")
            results["keyword_cooccurrence_analysis"] = {"error": str(e)}
        
        # 3. 时间序列趋势分析
        try:
            trend_results = self.trend_analyzer.analyze_temporal_trends(annotations)
            results["temporal_trend_analysis"] = trend_results
            results["algorithms_used"].append("temporal_trend")
            logger.info("✅ 时间序列趋势分析完成")
        except Exception as e:
            logger.error(f"❌ 时间序列趋势分析失败: {e}")
            results["temporal_trend_analysis"] = {"error": str(e)}
        
        # 4. 用户行为模式分析
        try:
            behavior_results = self.behavior_analyzer.analyze_user_behavior_patterns(annotations)
            results["user_behavior_analysis"] = behavior_results
            results["algorithms_used"].append("user_behavior")
            logger.info("✅ 用户行为模式分析完成")
        except Exception as e:
            logger.error(f"❌ 用户行为模式分析失败: {e}")
            results["user_behavior_analysis"] = {"error": str(e)}
        
        logger.info(f"高级智能分析完成，使用了 {len(results['algorithms_used'])} 个算法")
        return results