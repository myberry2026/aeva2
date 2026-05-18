"""
Android Intent 仓库 - 集中管理所有 Deep Links 和标准 Actions
"""

# 1. 标准意图：统一二元组 (Action, URI)
INTENT_TEMPLATES = {
    # --- Google 标准功能 (Google Standards) ---
    "email":    ("android.intent.action.SENDTO", "mailto:{}"), # 发邮件
    "call":     ("android.intent.action.VIEW", "tel:{}"),      # 拨号盘
    "sms":      ("android.intent.action.VIEW", "smsto:{}"),    # 短信页
    "map":      ("android.intent.action.VIEW", "geo:0,0?q={}"), # 地图搜索
    "route":    ("android.intent.action.VIEW", "https://www.google.com/maps/dir/?api=1&origin={origin}&destination={destination}"), # 导航
    "search":   ("android.intent.action.VIEW", "https://www.google.com/search?q={}"), # 全局搜索 (Google)
    "google_search": ("android.intent.action.VIEW", "https://www.google.com/search?q={}"), # 别名
    
    # --- 第三方 App (Third-Party Apps) ---
    "youtube":  ("android.intent.action.VIEW", "https://www.youtube.com/watch?v={}"), # 播放 YouTube 视频
    "twitter":  ("android.intent.action.VIEW", "https://twitter.com/{}"),           # 查看推特用户
    "twitter_search": ("android.intent.action.VIEW", "https://twitter.com/search?q={}"), # 搜索推特
    "reddit":   ("android.intent.action.VIEW", "https://www.reddit.com/r/{}"),        # 查看 Reddit 板块
    "reddit_search":  ("android.intent.action.VIEW", "https://www.reddit.com/search/?q={}"), # 搜索 Reddit
    
    # --- 系统设置 (System Settings) ---
    "settings": ("android.settings.SETTINGS", None),
    "wifi":     ("android.settings.WIFI_SETTINGS", None),
    "app_info": ("android.settings.APPLICATION_DETAILS_SETTINGS", "package:{}"),
    "alarm":    ("android.intent.action.SHOW_ALARMS", None),
}

# 2. 复杂任务：专门处理带 Extras 的映射
COMPLEX_TEMPLATES = {
    "calendar": (
        "android.intent.action.INSERT",
        "content://com.android.calendar/events",
        {"title": "title", "description": "description", "beginTime": "beginTime", "endTime": "endTime"}
    ),
}

def get_intent(task, query=None):
    """根据任务从不同仓库获取 Intent"""
    # 尝试解析 JSON 格式的字符串 query
    if isinstance(query, str) and query.strip().startswith('{'):
        try:
            import json
            query = json.loads(query)
        except:
            pass

    action, data_tpl, extra_map = None, None, {}
    
    # 先查复杂库
    if task in COMPLEX_TEMPLATES:
        action, data_tpl, extra_map = COMPLEX_TEMPLATES[task]
    # 再查标准库
    elif task in INTENT_TEMPLATES:
        action, data_tpl = INTENT_TEMPLATES[task]
    else:
        return None, None, []
    
    uri = None
    extras = []

    # A. 填充 URI
    if data_tpl:
        if isinstance(query, dict):
            try: uri = data_tpl.format(**query)
            except: uri = data_tpl
        else:
            uri = data_tpl.format(str(query or "").replace(" ", "+"))

    # B. 填充 Extras
    if extra_map and isinstance(query, dict):
        for k, v in query.items():
            if k in extra_map:
                val = str(v)
                prefix = "--ei" if val.isdigit() else "--es"
                extras.extend([prefix, extra_map[k], val])
                
    return action, uri, extras
