from __future__ import annotations

import re


SUPPORTED_PLATFORMS = {"web", "ios", "android", "hybrid", "generic"}


def infer_platform(raw_text: str) -> str:
    text = raw_text.lower()

    if any(k in text for k in ["wkwebview", "webview", "flutter", "react native", "rn bridge", "js bridge"]):
        return "hybrid"
    if any(k in text for k in ["ios", "ipa", "bundle id", "nsurlsession", "keychain", "sectrust"]):
        return "ios"
    if any(k in text for k in ["android", "apk", "aab", "okhttp", "retrofit", "jni", "frida"]):
        return "android"
    if "http://" in text or "https://" in text:
        return "web"
    if re.search(r"(?<!@)\b(?:[a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}\b", text):
        return "web"
    return "generic"


def resolve_platform(platform_arg: str, raw_text: str) -> str:
    value = (platform_arg or "").strip().lower()
    if not value or value == "auto":
        return infer_platform(raw_text)
    if value not in SUPPORTED_PLATFORMS:
        return "generic"
    return value


def _stage_contract() -> str:
    return (
        "每个阶段必须包含 5 项：\n"
        "- Confirmed facts\n"
        "- Key evidence\n"
        "- Current inference\n"
        "- Unverified points\n"
        "- Next step"
    )


def build_platform_reverse_request(raw_request: str, platform: str, focus_param: str = "") -> str:
    focus_text = focus_param.strip() or "目标参数"

    if platform == "web":
        guide = (
            "【平台】Web\n"
            f"【逆向测试重点】还原 {focus_text} 的生成链路并评估强度（仅防御性分析）\n"
            "按阶段执行：\n"
            "1. Recon（触发动作与请求序列）\n"
            "2. Communication Analysis（URL/headers/cookie/参数变化）\n"
            "3. Static Analysis（签名与依赖函数链）\n"
            "4. Dynamic Validation（关键中间值证据点）\n"
            "5. Reconstruction & Strength Assessment（0-10评分+改进建议）\n"
        )
    elif platform == "ios":
        guide = (
            "【平台】iOS\n"
            f"【逆向测试重点】还原 {focus_text} 的生成链路并评估强度（仅防御性分析）\n"
            "按阶段执行：\n"
            "1. Recon（关键页面/调用路径）\n"
            "2. Communication Analysis（NSURLSession/请求构建）\n"
            "3. Static Analysis（签名函数、SecTrust、Keychain、WKWebView）\n"
            "4. Dynamic Validation（入参/出参/中间值证据点）\n"
            "5. Reconstruction & Strength Assessment（0-10评分+改进建议）\n"
        )
    elif platform == "android":
        guide = (
            "【平台】Android\n"
            f"【逆向测试重点】还原 {focus_text} 的生成链路并评估强度（仅防御性分析）\n"
            "按阶段执行：\n"
            "1. Recon（关键页面/组件路径）\n"
            "2. Communication Analysis（okhttp/retrofit/请求构建）\n"
            "3. Static Analysis（Java/Kotlin到JNI/so关键链路）\n"
            "4. Dynamic Validation（入参/出参/中间值证据点）\n"
            "5. Reconstruction & Strength Assessment（0-10评分+改进建议）\n"
        )
    elif platform == "hybrid":
        guide = (
            "【平台】Hybrid\n"
            f"【逆向测试重点】还原 {focus_text} 在 H5 与 Native 跨层链路中的生成过程（仅防御性分析）\n"
            "按阶段执行：\n"
            "1. Recon（入口页面与桥接触发点）\n"
            "2. Communication Analysis（H5请求与Native参与边界）\n"
            "3. Static Analysis（WebView/WKWebView/Bridge路径）\n"
            "4. Dynamic Validation（跨层参数映射证据点）\n"
            "5. Reconstruction & Strength Assessment（0-10评分+改进建议）\n"
        )
    else:
        guide = (
            "【平台】待识别\n"
            f"【逆向测试重点】还原 {focus_text} 的生成链路并评估强度（仅防御性分析）\n"
            "先识别目标平台（Web/iOS/Android/Hybrid），再按对应平台流程执行。\n"
        )

    return (
        "你是内部应用安全逆向测试助手，仅做授权防御性评估，不提供攻击利用细节。\n"
        f"{guide}\n"
        f"{_stage_contract()}\n"
        f"【用户原始任务】{raw_request}"
    )

