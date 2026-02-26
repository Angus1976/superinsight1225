#!/usr/bin/env python3
"""向 Label Studio 导入多种典型演示数据集，让系统演示更完整。"""

import json
import os
import random
import requests
import sys

LS_URL = os.getenv("LABEL_STUDIO_URL", "http://localhost:8080")
LS_TOKEN = os.getenv("LABEL_STUDIO_API_TOKEN", "fdf4c143512bf61cc1a51ac7a2fa0f429131a7a8")
HEADERS = {"Authorization": f"Token {LS_TOKEN}", "Content-Type": "application/json"}


def create_project(title, description, label_config, color="#1f77b4"):
    """创建 Label Studio 项目。"""
    resp = requests.post(
        f"{LS_URL}/api/projects/",
        headers=HEADERS,
        json={
            "title": title,
            "description": description,
            "label_config": label_config,
            "color": color,
            "show_instruction": True,
            "show_skip_button": True,
        },
    )
    if resp.status_code not in (200, 201):
        print(f"  ❌ 创建项目失败: {title} - {resp.text[:200]}")
        return None
    project = resp.json()
    print(f"  ✅ 项目已创建: {title} (ID: {project['id']})")
    return project["id"]


def import_tasks(project_id, tasks):
    """向项目导入任务数据。"""
    resp = requests.post(
        f"{LS_URL}/api/projects/{project_id}/import",
        headers=HEADERS,
        json=tasks,
    )
    if resp.status_code not in (200, 201):
        print(f"  ❌ 导入任务失败: {resp.text[:200]}")
        return False
    print(f"  ✅ 已导入 {len(tasks)} 条任务")
    return True


# ─── 1. 文本情感分析 ───
SENTIMENT_CONFIG = """<View>
  <Header value="请判断以下文本的情感倾向"/>
  <Text name="text" value="$text"/>
  <Choices name="sentiment" toName="text" choice="single-radio">
    <Choice value="正面" alias="positive"/>
    <Choice value="负面" alias="negative"/>
    <Choice value="中性" alias="neutral"/>
  </Choices>
  <Textarea name="comment" toName="text" placeholder="备注（可选）" maxSubmissions="1"/>
</View>"""

SENTIMENT_TASKS = [
    {"text": "这款产品质量非常好，物超所值，强烈推荐！"},
    {"text": "发货速度很快，包装也很精美，下次还会回购。"},
    {"text": "客服态度非常好，耐心解答了我所有的问题。"},
    {"text": "产品和描述完全不符，质量很差，非常失望。"},
    {"text": "等了两周才收到货，而且包装破损严重。"},
    {"text": "退货流程太复杂了，客服也不配合，体验极差。"},
    {"text": "价格还行，质量一般般，没什么特别的。"},
    {"text": "收到了，还没用，外观看起来还可以。"},
    {"text": "这个价位能买到这样的产品，性价比很高。"},
    {"text": "用了一个月就坏了，售后说不在保修范围内。"},
    {"text": "朋友推荐的，用了之后确实不错，好评！"},
    {"text": "包装简陋，产品有划痕，不太满意。"},
    {"text": "功能齐全，操作简单，适合新手使用。"},
    {"text": "广告宣传和实际效果差距太大了。"},
    {"text": "第三次购买了，一如既往的好品质。"},
]


# ─── 2. 命名实体识别 (NER) ───
NER_CONFIG = """<View>
  <Header value="请标注文本中的实体"/>
  <Labels name="label" toName="text">
    <Label value="人名" background="#ff0000"/>
    <Label value="地名" background="#00ff00"/>
    <Label value="组织" background="#0000ff"/>
    <Label value="时间" background="#ff9900"/>
    <Label value="金额" background="#9900ff"/>
    <Label value="产品" background="#00cccc"/>
  </Labels>
  <Text name="text" value="$text"/>
</View>"""

NER_TASKS = [
    {"text": "2024年3月15日，阿里巴巴集团在杭州西湖区总部宣布，CEO张勇将主导一项价值50亿元的AI研发计划。"},
    {"text": "特斯拉CEO马斯克于上周在上海超级工厂发布了Model Y的最新改款车型，售价25.99万元起。"},
    {"text": "北京大学计算机科学系教授李明在2024年国际人工智能大会上发表了关于大语言模型的主题演讲。"},
    {"text": "腾讯公司昨日发布2023年第四季度财报，营收达到1552亿元，同比增长7%。"},
    {"text": "华为技术有限公司创始人任正非在深圳总部接受了央视记者的专访。"},
    {"text": "苹果公司将于2024年6月在旧金山举办WWDC开发者大会，预计发布iOS 18系统。"},
    {"text": "京东集团宣布投资100亿元在武汉建设亚洲最大的智能物流中心。"},
    {"text": "字节跳动旗下的TikTok在美国市场的月活跃用户已突破1.5亿。"},
    {"text": "小米集团创始人雷军宣布小米SU7电动汽车将于3月28日正式上市。"},
    {"text": "百度创始人李彦宏在北京发布了文心一言4.0版本，性能提升超过30%。"},
    {"text": "美团外卖在上海推出无人机配送服务，首批覆盖浦东新区10个社区。"},
    {"text": "中国科学院院士王志刚在南京紫金山天文台发现了一颗新的小行星。"},
]


# ─── 3. 文本分类（多标签）───
CLASSIFICATION_CONFIG = """<View>
  <Header value="请为以下新闻选择所有适用的分类标签"/>
  <Text name="text" value="$text"/>
  <Choices name="category" toName="text" choice="multiple">
    <Choice value="科技"/>
    <Choice value="财经"/>
    <Choice value="体育"/>
    <Choice value="娱乐"/>
    <Choice value="教育"/>
    <Choice value="健康"/>
    <Choice value="政治"/>
    <Choice value="社会"/>
  </Choices>
</View>"""

CLASSIFICATION_TASKS = [
    {"text": "OpenAI发布GPT-5模型，在多项基准测试中超越人类专家水平，引发科技界广泛关注。"},
    {"text": "央行宣布下调存款准备金率0.5个百分点，释放长期资金约1万亿元。"},
    {"text": "中国女排在巴黎奥运会预选赛中3:0横扫日本队，提前锁定奥运资格。"},
    {"text": "教育部发布新规：2025年起全国中小学将全面推行编程教育课程。"},
    {"text": "世界卫生组织发布报告：全球超过10亿人患有肥胖症，呼吁各国加强干预。"},
    {"text": "SpaceX星舰第四次试飞成功回收助推器，马斯克称火星移民计划提前。"},
    {"text": "A股三大指数集体上涨，沪指重回3000点，AI概念股领涨。"},
    {"text": "梅西宣布将在2024年美洲杯后退出阿根廷国家队。"},
    {"text": "清华大学与谷歌合作成立AI研究院，聚焦大模型安全与对齐研究。"},
    {"text": "国家医保局将120种创新药纳入医保目录，平均降价超过60%。"},
]


# ─── 4. 图像分类 ───
IMAGE_CLASS_CONFIG = """<View>
  <Header value="请对图像进行分类"/>
  <Image name="image" value="$image"/>
  <Choices name="category" toName="image" choice="single">
    <Choice value="猫"/>
    <Choice value="狗"/>
    <Choice value="鸟"/>
    <Choice value="鱼"/>
    <Choice value="其他"/>
  </Choices>
</View>"""

IMAGE_CLASS_TASKS = [
    {"image": "https://upload.wikimedia.org/wikipedia/commons/thumb/3/3a/Cat03.jpg/1200px-Cat03.jpg"},
    {"image": "https://upload.wikimedia.org/wikipedia/commons/thumb/2/26/YellowLabradorLooking_new.jpg/1200px-YellowLabradorLooking_new.jpg"},
    {"image": "https://upload.wikimedia.org/wikipedia/commons/thumb/4/45/A_small_cup_of_coffee.JPG/640px-A_small_cup_of_coffee.JPG"},
    {"image": "https://upload.wikimedia.org/wikipedia/commons/thumb/a/a7/Camponotus_flavomarginatus_ant.jpg/640px-Camponotus_flavomarginatus_ant.jpg"},
    {"image": "https://upload.wikimedia.org/wikipedia/commons/thumb/7/71/2010-kodiak-bear-1.jpg/640px-2010-kodiak-bear-1.jpg"},
]


# ─── 5. 对话意图识别 ───
INTENT_CONFIG = """<View>
  <Header value="请识别用户对话的意图"/>
  <Text name="text" value="$text"/>
  <Choices name="intent" toName="text" choice="single-radio">
    <Choice value="查询订单"/>
    <Choice value="退换货"/>
    <Choice value="投诉建议"/>
    <Choice value="产品咨询"/>
    <Choice value="技术支持"/>
    <Choice value="账户问题"/>
    <Choice value="闲聊"/>
  </Choices>
  <Rating name="urgency" toName="text" maxRating="5"/>
</View>"""

INTENT_TASKS = [
    {"text": "我上周买的那个订单到哪了？一直没收到。"},
    {"text": "这个东西质量有问题，我想退货。"},
    {"text": "你们的服务态度太差了，我要投诉！"},
    {"text": "请问这款手机支持5G吗？电池容量多大？"},
    {"text": "我的APP一直闪退，怎么解决？"},
    {"text": "我忘记密码了，怎么重置？"},
    {"text": "今天天气真好啊，你觉得呢？"},
    {"text": "订单号是20240315001，帮我查一下物流信息。"},
    {"text": "收到的商品颜色和图片不一样，能换吗？"},
    {"text": "你们有没有企业版的优惠方案？"},
    {"text": "系统提示网络错误，但我的网络是正常的。"},
    {"text": "能不能帮我把收货地址改一下？"},
    {"text": "这个产品和上一代相比有什么改进？"},
    {"text": "我的会员积分怎么突然少了？"},
    {"text": "你们周末有人值班吗？"},
]


# ─── 6. 文本摘要评估 ───
SUMMARY_CONFIG = """<View>
  <Header value="请评估AI生成的摘要质量"/>
  <Text name="original" value="$original"/>
  <Header value="AI 生成的摘要："/>
  <Text name="summary" value="$summary"/>
  <Rating name="accuracy" toName="summary" maxRating="5"/>
  <Choices name="quality" toName="summary" choice="single-radio">
    <Choice value="优秀"/>
    <Choice value="良好"/>
    <Choice value="一般"/>
    <Choice value="较差"/>
  </Choices>
  <Textarea name="feedback" toName="summary" placeholder="改进建议"/>
</View>"""

SUMMARY_TASKS = [
    {
        "original": "近日，中国科学院发布了2024年度十大科技进展，涵盖量子计算、人工智能、生物医药等多个领域。其中，量子计算机九章三号在特定问题上的计算速度比经典超级计算机快10的14次方倍，标志着中国在量子计算领域取得重大突破。",
        "summary": "中科院发布2024十大科技进展，量子计算机九章三号实现重大突破。",
    },
    {
        "original": "全球气候变化导致极端天气事件频发。2024年，全球平均气温较工业化前上升了1.5°C，多个国家遭遇创纪录的高温、洪水和干旱。联合国秘书长呼吁各国加速减排，并在2030年前将温室气体排放量减少45%。",
        "summary": "2024年全球气温上升1.5°C，极端天气频发，联合国呼吁加速减排。",
    },
    {
        "original": "人工智能在医疗领域的应用取得显著进展。谷歌DeepMind开发的AlphaFold 3能够预测几乎所有生物分子的结构，这一突破将加速新药研发过程。同时，多家医院开始使用AI辅助诊断系统，在肺癌早期筛查中的准确率达到97%。",
        "summary": "AI医疗应用进展显著：AlphaFold 3预测分子结构，AI肺癌筛查准确率97%。",
    },
    {
        "original": "中国新能源汽车产业持续高速发展。2024年前三季度，新能源汽车销量突破700万辆，同比增长35%。比亚迪、蔚来、小鹏等品牌在海外市场的份额也在快速增长，中国已成为全球最大的新能源汽车出口国。",
        "summary": "2024年中国新能源车销量超700万辆，成全球最大出口国。",
    },
]


# ─── 7. 关系抽取 ───
RELATION_CONFIG = """<View>
  <Header value="请标注文本中实体之间的关系"/>
  <Labels name="label" toName="text">
    <Label value="主体" background="#ff6600"/>
    <Label value="客体" background="#0066ff"/>
  </Labels>
  <Text name="text" value="$text"/>
  <Choices name="relation" toName="text" choice="single-radio">
    <Choice value="创始人"/>
    <Choice value="CEO"/>
    <Choice value="收购"/>
    <Choice value="投资"/>
    <Choice value="合作"/>
    <Choice value="竞争"/>
    <Choice value="子公司"/>
  </Choices>
</View>"""

RELATION_TASKS = [
    {"text": "马云是阿里巴巴集团的创始人。"},
    {"text": "微软以687亿美元收购了动视暴雪。"},
    {"text": "腾讯投资了拼多多的早期融资轮。"},
    {"text": "华为与比亚迪在智能汽车领域展开深度合作。"},
    {"text": "抖音是字节跳动旗下的短视频平台。"},
    {"text": "苹果和三星在智能手机市场展开激烈竞争。"},
    {"text": "雷军创立了小米科技有限公司。"},
    {"text": "亚马逊以137亿美元收购了全食超市。"},
    {"text": "百度与吉利合资成立了集度汽车。"},
    {"text": "OpenAI的CEO是Sam Altman。"},
]


# ─── 8. 问答对质量评估 ───
QA_CONFIG = """<View>
  <Header value="请评估问答对的质量"/>
  <Header value="问题："/>
  <Text name="question" value="$question"/>
  <Header value="回答："/>
  <Text name="answer" value="$answer"/>
  <Choices name="correctness" toName="answer" choice="single-radio">
    <Choice value="完全正确"/>
    <Choice value="部分正确"/>
    <Choice value="不正确"/>
    <Choice value="无法判断"/>
  </Choices>
  <Choices name="completeness" toName="answer" choice="single-radio">
    <Choice value="完整"/>
    <Choice value="部分完整"/>
    <Choice value="不完整"/>
  </Choices>
  <Rating name="overall" toName="answer" maxRating="5"/>
</View>"""

QA_TASKS = [
    {"question": "Python中列表和元组的区别是什么？", "answer": "列表是可变的，用方括号[]表示；元组是不可变的，用圆括号()表示。列表可以增删改元素，元组创建后不能修改。"},
    {"question": "什么是机器学习中的过拟合？", "answer": "过拟合是指模型在训练数据上表现很好，但在新数据上表现差。通常是因为模型过于复杂，学习了训练数据中的噪声。"},
    {"question": "HTTP和HTTPS的区别？", "answer": "HTTPS在HTTP基础上加入了SSL/TLS加密层，数据传输更安全。HTTPS使用443端口，HTTP使用80端口。"},
    {"question": "什么是Docker？", "answer": "Docker是一个容器化平台，可以将应用及其依赖打包成容器，实现一致的运行环境，便于部署和扩展。"},
    {"question": "解释一下RESTful API的设计原则。", "answer": "RESTful API基于HTTP协议，使用URL定位资源，用HTTP方法（GET/POST/PUT/DELETE）操作资源，无状态，返回JSON格式数据。"},
    {"question": "什么是数据库索引？为什么要使用索引？", "answer": "索引是数据库中用于加速查询的数据结构，类似书的目录。使用索引可以大幅提高查询速度，但会增加写入开销和存储空间。"},
    {"question": "Git中rebase和merge的区别？", "answer": "merge会创建一个新的合并提交，保留完整历史；rebase会将提交重新应用到目标分支上，使历史更线性。"},
    {"question": "什么是微服务架构？", "answer": "微服务架构将应用拆分为多个小型、独立部署的服务，每个服务负责特定功能，通过API通信，便于独立开发和扩展。"},
]


# ─── 9. 销售数据标注（表格数据）───
SALES_CONFIG = """<View>
  <Header value="请审核销售数据的分类和标签"/>
  <Text name="record" value="$record"/>
  <Choices name="category" toName="record" choice="single-radio">
    <Choice value="高价值客户"/>
    <Choice value="中价值客户"/>
    <Choice value="低价值客户"/>
    <Choice value="流失风险"/>
  </Choices>
  <Choices name="trend" toName="record" choice="single-radio">
    <Choice value="上升趋势"/>
    <Choice value="稳定"/>
    <Choice value="下降趋势"/>
  </Choices>
  <Textarea name="note" toName="record" placeholder="分析备注"/>
</View>"""

SALES_TASKS = [
    {"record": "客户: 张三 | 月均消费: ¥15,800 | 购买频次: 12次/月 | 最近购买: 2天前 | 会员等级: 钻石"},
    {"record": "客户: 李四 | 月均消费: ¥3,200 | 购买频次: 4次/月 | 最近购买: 5天前 | 会员等级: 金卡"},
    {"record": "客户: 王五 | 月均消费: ¥580 | 购买频次: 1次/月 | 最近购买: 45天前 | 会员等级: 普通"},
    {"record": "客户: 赵六 | 月均消费: ¥8,900 | 购买频次: 8次/月 | 最近购买: 1天前 | 会员等级: 白金"},
    {"record": "客户: 孙七 | 月均消费: ¥12,500 | 购买频次: 6次/月 | 最近购买: 90天前 | 会员等级: 钻石"},
    {"record": "客户: 周八 | 月均消费: ¥950 | 购买频次: 2次/月 | 最近购买: 15天前 | 会员等级: 银卡"},
    {"record": "客户: 吴九 | 月均消费: ¥25,000 | 购买频次: 15次/月 | 最近购买: 今天 | 会员等级: 至尊"},
    {"record": "客户: 郑十 | 月均消费: ¥200 | 购买频次: 0.5次/月 | 最近购买: 60天前 | 会员等级: 普通"},
]


# ─── 10. 文本相似度评估 ───
SIMILARITY_CONFIG = """<View>
  <Header value="请评估两段文本的语义相似度"/>
  <Header value="文本 A："/>
  <Text name="text_a" value="$text_a"/>
  <Header value="文本 B："/>
  <Text name="text_b" value="$text_b"/>
  <Rating name="similarity" toName="text_a" maxRating="5"/>
  <Choices name="type" toName="text_a" choice="single-radio">
    <Choice value="语义相同"/>
    <Choice value="语义相近"/>
    <Choice value="部分相关"/>
    <Choice value="不相关"/>
    <Choice value="语义矛盾"/>
  </Choices>
</View>"""

SIMILARITY_TASKS = [
    {"text_a": "今天天气很好，适合出去散步。", "text_b": "今天阳光明媚，是个散步的好日子。"},
    {"text_a": "这家餐厅的菜很好吃。", "text_b": "这家饭店的食物味道不错。"},
    {"text_a": "我喜欢在周末看电影。", "text_b": "股票市场今天大幅下跌。"},
    {"text_a": "Python是一种编程语言。", "text_b": "蟒蛇是一种大型爬行动物。"},
    {"text_a": "机器学习需要大量数据。", "text_b": "深度学习模型的训练依赖海量数据集。"},
    {"text_a": "这个产品很便宜。", "text_b": "这个产品价格昂贵。"},
    {"text_a": "他跑得很快。", "text_b": "他的速度非常惊人。"},
    {"text_a": "北京是中国的首都。", "text_b": "中华人民共和国的首都是北京。"},
]


# ─── 项目定义列表 ───
PROJECTS = [
    {
        "title": "📊 电商评论情感分析",
        "desc": "对电商平台用户评论进行正面/负面/中性情感分类，用于产品口碑监控和用户满意度分析。",
        "config": SENTIMENT_CONFIG,
        "tasks": SENTIMENT_TASKS,
        "color": "#52c41a",
    },
    {
        "title": "🏷️ 中文命名实体识别 (NER)",
        "desc": "标注中文文本中的人名、地名、组织、时间、金额等实体，用于信息抽取和知识图谱构建。",
        "config": NER_CONFIG,
        "tasks": NER_TASKS,
        "color": "#1890ff",
    },
    {
        "title": "📰 新闻多标签分类",
        "desc": "为新闻文本分配多个分类标签（科技/财经/体育/娱乐等），支持多标签分类模型训练。",
        "config": CLASSIFICATION_CONFIG,
        "tasks": CLASSIFICATION_TASKS,
        "color": "#722ed1",
    },
    {
        "title": "🖼️ 图像分类标注",
        "desc": "对图像进行分类标注，支持动物识别、物体分类等计算机视觉任务。",
        "config": IMAGE_CLASS_CONFIG,
        "tasks": IMAGE_CLASS_TASKS,
        "color": "#eb2f96",
    },
    {
        "title": "💬 客服对话意图识别",
        "desc": "识别客服对话中用户的意图（查询订单/退换货/投诉/咨询等），用于智能客服系统训练。",
        "config": INTENT_CONFIG,
        "tasks": INTENT_TASKS,
        "color": "#fa8c16",
    },
    {
        "title": "📝 AI摘要质量评估",
        "desc": "评估AI生成的文本摘要的准确性、完整性和质量，用于RLHF训练数据收集。",
        "config": SUMMARY_CONFIG,
        "tasks": SUMMARY_TASKS,
        "color": "#13c2c2",
    },
    {
        "title": "🔗 实体关系抽取",
        "desc": "标注文本中实体之间的关系（创始人/收购/投资/合作等），用于知识图谱构建。",
        "config": RELATION_CONFIG,
        "tasks": RELATION_TASKS,
        "color": "#2f54eb",
    },
    {
        "title": "❓ 问答对质量评估",
        "desc": "评估问答对的正确性、完整性和整体质量，用于QA系统和RAG评估。",
        "config": QA_CONFIG,
        "tasks": QA_TASKS,
        "color": "#a0d911",
    },
    {
        "title": "💰 销售数据客户分类",
        "desc": "根据销售数据对客户进行价值分类和趋势判断，用于CRM和销售预测模型。",
        "config": SALES_CONFIG,
        "tasks": SALES_TASKS,
        "color": "#f5222d",
    },
    {
        "title": "🔄 文本语义相似度评估",
        "desc": "评估两段文本的语义相似度，用于语义搜索、去重和文本匹配模型训练。",
        "config": SIMILARITY_CONFIG,
        "tasks": SIMILARITY_TASKS,
        "color": "#faad14",
    },
]


def main():
    """主函数：创建所有演示项目并导入数据。"""
    print("=" * 60)
    print("🚀 开始导入 Label Studio 演示数据集")
    print("=" * 60)

    # 检查连接
    try:
        resp = requests.get(f"{LS_URL}/api/projects/", headers=HEADERS, timeout=5)
        if resp.status_code != 200:
            print(f"❌ 无法连接 Label Studio: HTTP {resp.status_code}")
            sys.exit(1)
        existing = resp.json().get("count", 0)
        print(f"✅ 已连接 Label Studio ({LS_URL})")
        print(f"📊 当前已有 {existing} 个项目\n")
    except requests.ConnectionError:
        print(f"❌ 无法连接 Label Studio: {LS_URL}")
        sys.exit(1)

    created = 0
    for proj in PROJECTS:
        print(f"\n{'─' * 40}")
        print(f"📁 创建项目: {proj['title']}")
        pid = create_project(proj["title"], proj["desc"], proj["config"], proj["color"])
        if pid is None:
            continue
        import_tasks(pid, proj["tasks"])
        created += 1

    print(f"\n{'=' * 60}")
    print(f"✅ 完成！共创建 {created} 个演示项目")
    total_tasks = sum(len(p["tasks"]) for p in PROJECTS)
    print(f"📊 共导入 {total_tasks} 条标注任务")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
