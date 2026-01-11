import os
from Bio import Entrez
from datetime import datetime

# ================= 配置区域 =================
Entrez.email = "your.email@example.com"
SEARCH_TERM = "In vivo CAR-T"
# 过去30天
TIME_RANGE_DAYS = 30
# 确保能抓取到所有文章，设置一个较大的值
MAX_RESULTS = 1000 

# 🌟 内置常用期刊影响因子库 (基于2023/2024数据估算)
# 你可以随时手动往这里添加你关注的期刊
JOURNAL_IF_MAP = {
    "Nature": 64.8, "Science": 56.9, "Cell": 64.5, "New England Journal of Medicine": 96.2,
    "The Lancet": 168.9, "Nature Medicine": 82.9, "Cancer Discovery": 28.2,
    "Cancer Cell": 48.8, "Immunity": 32.4, "Blood": 20.3,
    "Journal of Clinical Oncology": 45.3, "Nature Biotechnology": 46.9,
    "Signal Transduction and Targeted Therapy": 39.3, "Molecular Cancer": 37.3,
    "Nature Reviews Drug Discovery": 120.1, "Nature Reviews Cancer": 78.5,
    "Nature Reviews Immunology": 100.3, "Nature Reviews Clinical Oncology": 78.8,
    "Nature Communications": 16.6, "Science Immunology": 24.8,
    "Science Translational Medicine": 17.1, "JAMA Oncology": 28.4,
    "Journal of Hematology & Oncology": 28.5, "Leukemia": 12.8,
    "Molecular Therapy": 12.4, "Clinical Cancer Research": 11.5,
    "Frontiers in Immunology": 7.3, "Scientific Reports": 4.6,
    "PLoS One": 3.7, "Oncogene": 8.0, "Theranostics": 12.4,
    "Journal for ImmunoTherapy of Cancer": 10.9, "Bone Marrow Transplantation": 4.5,
    "Cytotherapy": 5.4, "Molecular Therapy - Oncolytics": 6.3
}
# ===========================================

def get_impact_factor(journal_name):
    """根据期刊名查找影响因子"""
    # 尝试直接匹配
    if journal_name in JOURNAL_IF_MAP:
        return JOURNAL_IF_MAP[journal_name]
    
    # 尝试忽略大小写匹配
    for k, v in JOURNAL_IF_MAP.items():
        if k.lower() == journal_name.lower():
            return v
    
    return "N/A" # 未收录

def search_pubmed(base_term, is_review=False):
    """搜索过去30天的文章"""
    if is_review:
        term = f"({base_term}) AND Review[Publication Type]"
    else:
        term = f"({base_term}) AND Journal Article[Publication Type] NOT Review[Publication Type]"

    try:
        # reldate 修改为 TIME_RANGE_DAYS (30)
        handle = Entrez.esearch(db="pubmed", term=term, retmax=MAX_RESULTS, 
                                reldate=TIME_RANGE_DAYS, datetype="edat", sort="date")
        record = Entrez.read(handle)
        handle.close()
        return record["IdList"]
    except Exception as e:
        print(f"搜索出错: {e}")
        return []

def fetch_details(id_list):
    """批量获取详情 (PubMed API一次最多建议 fetch 200-300篇，我们分批处理)"""
    if not id_list:
        return []
    
    all_records = []
    batch_size = 200 # 分批大小
    
    print(f"正在获取 {len(id_list)} 篇文章详情...")
    
    for i in range(0, len(id_list), batch_size):
        batch_ids = id_list[i:i+batch_size]
        ids = ",".join(batch_ids)
        try:
            handle = Entrez.efetch(db="pubmed", id=ids, retmode="xml")
            records = Entrez.read(handle)
            handle.close()
            # 确保结果是列表
            if 'PubmedArticle' in records:
                all_records.extend(records["PubmedArticle"])
        except Exception as e:
            print(f"分批获取详情失败: {e}")
            
    return all_records

def format_article_list(articles):
    if not articles:
        return "*(该时间段内暂无新增文献)*\n\n"
    
    text = ""
    # 按影响因子排序 (可选，如果想按时间排就把下面这行注释掉)
    # articles.sort(key=lambda x: get_impact_factor_val(x), reverse=True)

    for article in articles:
        try:
            title = article['MedlineCitation']['Article']['ArticleTitle']
        except:
            title = "无标题"
            
        pmid = article['MedlineCitation']['PMID']
        url = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
        
        try:
            journal = article['MedlineCitation']['Article']['Journal']['Title']
            # 获取影响因子
            if_val = get_impact_factor(journal)
        except:
            journal = "未知期刊"
            if_val = "N/A"
            
        # 增加IF的显示徽章/文字
        if_display = f"**IF: {if_val}**" if if_val != "N/A" else "IF: N/A"

        try:
            abstract_list = article['MedlineCitation']['Article']['Abstract']['AbstractText']
            abstract = " ".join([str(x) for x in abstract_list])
            abstract_preview = abstract[:200] + "..." 
        except:
            abstract_preview = "暂无摘要预览"

        text += f"### [{title}]({url})\n"
        text += f"- 📚 **期刊**: *{journal}* | 📈 {if_display}\n" # 这一行增加了IF
        text += f"- **摘要**: {abstract_preview}\n\n"
    return text

def update_readme(reviews, articles):
    date_str = datetime.now().strftime("%Y-%m-%d")
    
    content = f"# 🧬 In vivo CAR-T 文献月报\n\n"
    content += f"> 📅 更新日期: {date_str} | ⏱️ 统计范围: 过去 {TIME_RANGE_DAYS} 天 | 🔍 关键词: {SEARCH_TERM}\n\n"
    
    content += f"## 📘 最新综述 (Reviews) - 共 {len(reviews)} 篇\n"
    content += "---\n"
    content += format_article_list(reviews)
    
    content += f"## 🔬 最新研究论文 (Articles) - 共 {len(articles)} 篇\n"
    content += "---\n"
    content += format_article_list(articles)
    
    with open("README.md", "w", encoding="utf-8") as f:
        f.write(content)

if __name__ == "__main__":
    print(f"🔍 开始检索过去 {TIME_RANGE_DAYS} 天 '{SEARCH_TERM}' 相关文献...")
    
    # 1. 搜综述
    review_ids = search_pubmed(SEARCH_TERM, is_review=True)
    review_details = fetch_details(review_ids)
    
    # 2. 搜论文
    article_ids = search_pubmed(SEARCH_TERM, is_review=False)
    article_details = fetch_details(article_ids)
    
    # 3. 更新文件
    print(f"✅ 处理完成: 综述 {len(review_details)} 篇，论文 {len(article_details)} 篇。")
    update_readme(review_details, article_details)
