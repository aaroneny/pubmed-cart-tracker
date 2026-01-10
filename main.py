import os
from Bio import Entrez
from datetime import datetime, timedelta

# ================= 配置区域 =================
Entrez.email = "your.email@example.com" # 请保留你之前填写的邮箱
SEARCH_TERM = "In vivo CAR-T"
# 分别限制每个分类显示的条数
MAX_RESULTS_PER_TYPE = 10 
# ===========================================

def search_pubmed(base_term, is_review=False):
    """
    根据类型搜索最近7天的文章
    is_review=True: 搜索综述
    is_review=False: 搜索普通论著
    """
    # 构造高级查询语法
    if is_review:
        # 关键词 + 必须是综述
        term = f"({base_term}) AND Review[Publication Type]"
    else:
        # 关键词 + 必须是期刊论文 + 排除综述 (避免重复)
        term = f"({base_term}) AND Journal Article[Publication Type] NOT Review[Publication Type]"

    try:
        # reldate=7: 限制在最近7天
        # datetype="edat": 使用"录入日期" (Entrez Date)，确保抓到刚上传的新文
        handle = Entrez.esearch(db="pubmed", term=term, retmax=MAX_RESULTS_PER_TYPE, 
                                reldate=7, datetype="edat", sort="date")
        record = Entrez.read(handle)
        handle.close()
        return record["IdList"]
    except Exception as e:
        print(f"搜索出错: {e}")
        return []

def fetch_details(id_list):
    """根据 ID 获取文章详情 (保持不变)"""
    if not id_list:
        return []
    ids = ",".join(id_list)
    try:
        handle = Entrez.efetch(db="pubmed", id=ids, retmode="xml")
        records = Entrez.read(handle)
        handle.close()
        return records["PubmedArticle"]
    except Exception as e:
        print(f"获取详情出错: {e}")
        return []

def format_article_list(articles):
    """将文章列表格式化为 Markdown 文本"""
    if not articles:
        return "*(本周暂无该类目新增文献)*\n\n"
    
    text = ""
    for article in articles:
        # 提取标题
        try:
            title = article['MedlineCitation']['Article']['ArticleTitle']
        except:
            title = "无标题"
            
        # 提取 PMID 和 链接
        pmid = article['MedlineCitation']['PMID']
        url = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
        
        # 提取期刊名和年份
        try:
            journal = article['MedlineCitation']['Article']['Journal']['Title']
        except:
            journal = "未知期刊"
            
        # 提取摘要
        try:
            abstract_list = article['MedlineCitation']['Article']['Abstract']['AbstractText']
            abstract = " ".join([str(x) for x in abstract_list])
            abstract_preview = abstract[:150] + "..." # 缩短预览
        except:
            abstract_preview = "暂无摘要预览"

        # 组合格式
        text += f"### [{title}]({url})\n"
        text += f"- **期刊**: *{journal}*\n"
        text += f"- **摘要**: {abstract_preview}\n\n"
    return text

def update_readme(reviews, articles):
    """更新 README，分为两块区域"""
    date_str = datetime.now().strftime("%Y-%m-%d")
    
    content = f"# 🧬 In vivo CAR-T 本周最新文献周报\n\n"
    content += f"> 更新日期: {date_str} | 统计范围: 过去 7 天 | 关键词: {SEARCH_TERM}\n\n"
    
    # 第一部分：综述
    content += "## 📘 最新综述 (Reviews)\n"
    content += "---\n"
    content += format_article_list(reviews)
    
    # 第二部分：研究论文
    content += "## 🔬 最新研究论文 (Articles)\n"
    content += "---\n"
    content += format_article_list(articles)
    
    with open("README.md", "w", encoding="utf-8") as f:
        f.write(content)

if __name__ == "__main__":
    print(f"🔍 开始检索本周 '{SEARCH_TERM}' 相关文献...")
    
    # 1. 搜综述
    print("正在检索综述...")
    review_ids = search_pubmed(SEARCH_TERM, is_review=True)
    review_details = fetch_details(review_ids) if review_ids else []
    
    # 2. 搜论文
    print("正在检索研究论文...")
    article_ids = search_pubmed(SEARCH_TERM, is_review=False)
    article_details = fetch_details(article_ids) if article_ids else []
    
    # 3. 更新文件
    print(f"找到 {len(review_details)} 篇综述，{len(article_details)} 篇论文。")
    update_readme(review_details, article_details)
    print("✅ README.md 更新完成！")
