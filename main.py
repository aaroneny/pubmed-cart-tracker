import os
from Bio import Entrez
from datetime import datetime

# ================= 配置区域 =================
# PubMed 要求必须提供邮箱，以便联系（请随便填个格式正确的邮箱，或填你自己的）
Entrez.email = "your.email@example.com"
# 搜索关键词
SEARCH_TERM = "In vivo CAR-T"
# 每次获取多少篇最新文章
MAX_RESULTS = 5
# ===========================================

def search_pubmed(term):
    """搜索 PubMed 并返回 ID 列表"""
    try:
        # esearch: 搜索接口
        handle = Entrez.esearch(db="pubmed", term=term, retmax=MAX_RESULTS, sort="date")
        record = Entrez.read(handle)
        handle.close()
        return record["IdList"]
    except Exception as e:
        print(f"搜索出错: {e}")
        return []

def fetch_details(id_list):
    """根据 ID 获取文章详细信息"""
    if not id_list:
        return []
    ids = ",".join(id_list)
    try:
        # efetch: 获取详情接口
        handle = Entrez.efetch(db="pubmed", id=ids, retmode="xml")
        records = Entrez.read(handle)
        handle.close()
        return records["PubmedArticle"]
    except Exception as e:
        print(f"获取详情出错: {e}")
        return []

def update_readme(articles):
    """将结果写入 README.md"""
    # 获取当前日期
    date_str = datetime.now().strftime("%Y-%m-%d")
    
    content = f"# 🧬 In vivo CAR-T 最新文献日报\n\n"
    content += f"> 更新时间: {date_str} | 关键词: {SEARCH_TERM}\n\n"
    content += "---\n\n"

    for article in articles:
        # 提取标题
        title = article['MedlineCitation']['Article']['ArticleTitle']
        # 提取 ID 生成链接
        pmid = article['MedlineCitation']['PMID']
        url = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
        # 尝试提取摘要（有些文章可能没摘要）
        try:
            abstract_list = article['MedlineCitation']['Article']['Abstract']['AbstractText']
            # 将摘要列表拼接成字符串
            abstract = " ".join([str(x) for x in abstract_list])
            # 截取前200个字符避免太长
            abstract_preview = abstract[:200] + "..."
        except KeyError:
            abstract_preview = "暂无摘要预览"

        # 写入 Markdown 格式
        content += f"### [{title}]({url})\n"
        content += f"- **PMID**: {pmid}\n"
        content += f"- **摘要预览**: {abstract_preview}\n\n"
    
    # 写入文件（覆盖模式，每次都看最新的）
    with open("README.md", "w", encoding="utf-8") as f:
        f.write(content)

if __name__ == "__main__":
    print(f"开始搜索: {SEARCH_TERM}...")
    ids = search_pubmed(SEARCH_TERM)
    print(f"找到 {len(ids)} 篇最新文章")
    
    if ids:
        articles = fetch_details(ids)
        update_readme(articles)
        print("README.md 更新成功！")
    else:
        print("未找到相关文章。")
