MAJOR = {
    "USD",
    "EUR",
    "GBP",
    "JPY",
    "HKD",
    "MOP",
    "CAD",
    "AUD",
    "NZD",
    "CHF",
    "SGD",
    "KRW",
    "RUB",
    "SEK",
    "NOK",
    "DKK",
    "PLN",
    "CZK",
    "HUF",
    "ILS",
    "AED",
    "SAR",
}

LOW_PRICE = {
    "TRY",
    "ARS",
    "INR",
    "IDR",
    "VND",
    "PHP",
    "MYR",
    "THB",
    "PKR",
    "BDT",
    "EGP",
    "NGN",
    "UAH",
    "KZT",
    "UZS",
    "BRL",
    "MXN",
    "COP",
    "CLP",
    "PEN",
    "ZAR",
}

HIGH_RISK = {
    "TRY",
    "ARS",
    "EGP",
    "NGN",
    "PKR",
    "LKR",
    "GHS",
    "ZMW",
    "ETB",
    "LBP",
    "SYP",
    "SDG",
    "SSP",
    "VES",
    "IRR",
    "AFN",
    "MMK",
    "YER",
    "RUB",
    "UAH",
}

ZH_NAMES = {
    "AED": "阿联酋迪拉姆",
    "AFN": "阿富汗尼",
    "ARS": "阿根廷比索",
    "AUD": "澳大利亚元",
    "BDT": "孟加拉塔卡",
    "BRL": "巴西雷亚尔",
    "CAD": "加拿大元",
    "CHF": "瑞士法郎",
    "CLP": "智利比索",
    "CNY": "人民币",
    "COP": "哥伦比亚比索",
    "CZK": "捷克克朗",
    "DKK": "丹麦克朗",
    "EGP": "埃及镑",
    "ETB": "埃塞俄比亚比尔",
    "EUR": "欧元",
    "GBP": "英镑",
    "GHS": "加纳塞地",
    "HKD": "港币",
    "HUF": "匈牙利福林",
    "IDR": "印度尼西亚盾",
    "ILS": "以色列新谢克尔",
    "INR": "印度卢比",
    "IRR": "伊朗里亚尔",
    "JPY": "日元",
    "KES": "肯尼亚先令",
    "KRW": "韩元",
    "KZT": "哈萨克斯坦坚戈",
    "LBP": "黎巴嫩镑",
    "LKR": "斯里兰卡卢比",
    "MMK": "缅甸元",
    "MOP": "澳门元",
    "MXN": "墨西哥比索",
    "MYR": "马来西亚林吉特",
    "NGN": "尼日利亚奈拉",
    "NOK": "挪威克朗",
    "NZD": "新西兰元",
    "PEN": "秘鲁索尔",
    "PHP": "菲律宾比索",
    "PKR": "巴基斯坦卢比",
    "PLN": "波兰兹罗提",
    "RUB": "俄罗斯卢布",
    "SAR": "沙特里亚尔",
    "SDG": "苏丹镑",
    "SEK": "瑞典克朗",
    "SGD": "新加坡元",
    "SYP": "叙利亚镑",
    "THB": "泰铢",
    "TRY": "土耳其里拉",
    "UAH": "乌克兰格里夫纳",
    "USD": "美元",
    "UZS": "乌兹别克斯坦苏姆",
    "VES": "委内瑞拉玻利瓦尔",
    "VND": "越南盾",
    "YER": "也门里亚尔",
    "ZAR": "南非兰特",
    "ZMW": "赞比亚克瓦查",
}

FLAG_OVERRIDES = {
    "ANG": "🇨🇼",
    "EUR": "🇪🇺",
    "XAF": "🌍",
    "XCD": "🌎",
    "XCG": "🇨🇼",
    "XOF": "🌍",
    "XPF": "🌏",
}

FLAG_REGION_OVERRIDES = {
    "ANG": "cw",
    "EUR": "eu",
    "XCG": "cw",
}

SHARED_REGION_CURRENCIES = {"XAF", "XCD", "XOF", "XPF"}


def flag_for(code: str) -> str:
    if code in FLAG_OVERRIDES:
        return FLAG_OVERRIDES[code]
    region = code[:2]
    if len(region) != 2 or not region.isalpha():
        return "🌐"
    return "".join(chr(127397 + ord(letter)) for letter in region.upper())


def flag_region_for(code: str) -> str | None:
    """Return the local SVG region code, or None for shared-region currencies."""
    if code in SHARED_REGION_CURRENCIES:
        return None
    if code in FLAG_REGION_OVERRIDES:
        return FLAG_REGION_OVERRIDES[code]
    region = code[:2].lower()
    return region if len(region) == 2 and region.isalpha() else None


def flags_for(code: str) -> dict[str, bool]:
    return {
        "is_major": code in MAJOR,
        "is_low_price": code in LOW_PRICE,
        "is_high_risk": code in HIGH_RISK,
    }
