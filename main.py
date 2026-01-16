import requests
from Bio import Entrez
import datetime
from deep_translator import GoogleTranslator

# --- 配置区域 ---
# 请务必替换为你自己的邮箱，这是 PubMed (NCBI) 的要求，否则可能被封 IP
Entrez.email = "dlu_fangenyue@163.com"  
KEYWORDS = '"In vivo CAR-T"[Title/Abstract]'

def translate_to_chinese(text):
    """
    使用免费接口将英文翻译成中文
    """
    try:
        # 使用 Google Translate 免费接口 (Github Actions 服务器通常可以直接访问)
        translator = GoogleTranslator(source='auto', target='zh-CN')
        return translator.translate(text)
    except Exception as e:
        print(f"翻译失败: {e}")
        return text  # 翻译失败则返回原文，保证程序不崩

def extract_conclusion(abstract_text):
    """
    逻辑：
    1. 尝试寻找 'Conclusion' 或 'Discussion' 等关键词，提取其后的内容。
    2. 如果找不到，简单粗暴地提取摘要的最后两句话。
    """
    if not abstract_text:
        return "暂无摘要"

    text = abstract_text.strip()
    upper_text = text.upper()
    
    # 策略A：寻找明确的结构标签
    # 很多医学论文摘要最后会写 "CONCLUSIONS: ..."
    for keyword in ["CONCLUSION:", "CONCLUSIONS:", "DISCUSSION:"]:
        if keyword in upper_text:
            # 从关键词位置往后截取
            index = upper_text.rfind(keyword)
            # 截取掉 "CONCLUSION:" 本身
            content = text[index + len(keyword):].strip()
            if content: 
                return content

    # 策略B：没有标签，提取最后两句
    sentences = text.split('. ')
    # 过滤掉空字符串
    sentences = [s for s in sentences if s.strip()]
    
    if len(sentences) >= 2:
        # 取最后两句，并补上句号
        return ". ".join(sentences[-2:]) + "."
    elif len(sentences) == 1:
        return sentences[0] + "."
    
    return text

def fetch_papers():
    # 获取今天的日期
    today = datetime.date.today()
    print(f"开始执行... 日期: {today}")
    
    # 搜索过去 7 天的文章
    try:
        handle = Entrez.esearch(db="pubmed", term=KEYWORDS, reldate=7, datetype="pdat", retmax=10)
        record = Entrez.read(handle)
        id_list = record["IdList"]
    except Exception as e:
        print(f"搜索 PubMed 出错: {e}")
        return []
    
    papers = []
    if id_list:
        try:
            # 获取详细信息
            handle = Entrez.efetch(db="pubmed", id=id_list, retmode="xml")
            records = Entrez.read(handle)
            
            for article in records['PubmedArticle']:
                try:
                    # 1. 标题
                    title = article['MedlineCitation']['Article']['ArticleTitle']
                    
                    # 2. 期刊
                    journal = article['MedlineCitation']['Article']['Journal']['Title']
                    
                    # 3. 摘要处理
                    abstract_list = article['MedlineCitation']['Article'].get('Abstract', {}).get('AbstractText', [])
                    if isinstance(abstract_list, list):
                        full_abstract = " ".join([str(x) for x in abstract_list])
                    else:
                        full_abstract = str(abstract_list)

                    # --- 核心：提取结论 -> 翻译 ---
                    print(f"处理文章: {title[:30]}...")
                    conclusion_en = extract_conclusion(full_abstract)
                    highlight_cn = translate_to_chinese(conclusion_en)

                    # 4. 链接
                    pmid = article['MedlineCitation']['PMID']
                    link = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
                    
                    papers.append({
                        "title": title,
                        "journal": journal,
                        "highlight": highlight_cn, 
                        "link": link
                    })
                except Exception as e:
                    print(f"跳过一篇文章 (解析错误): {e}")
                    continue
        except Exception as e:
            print(f"获取文章详情出错: {e}")

    return papers

def update_readme(papers):
    current_date = datetime.datetime.now().strftime('%Y-%m-%d')
    
    # README 头部内容
    content = f"# 🧬 In vivo CAR-T 每日追踪\n\n"
    content += f"📅 **更新日期**: {current_date}\n\n"
    content += f"> 💡 **说明**: 下方展示过去 7 天的新文献，内容为自动提取的中文版结论。\n\n"
    content += "---\n\n"
    
    if not papers:
        content += "📭 **过去 7 天未发现相关新文献。**\n"
    
    for paper in papers:
        content += f"### 📄 [{paper['title']}]({paper['link']})\n"
        content += f"- **期刊**: *{paper['journal']}*\n"
        # 这里用引用块展示翻译后的中文结论
        content += f"- **核心结论**: \n> {paper['highlight']}\n\n"
        content += "---\n"
        
    with open("README.md", "w", encoding="utf-8") as f:
        f.write(content)

if __name__ == "__main__":
    papers = fetch_papers()
    update_readme(papers)
    print("README 更新完成。")
