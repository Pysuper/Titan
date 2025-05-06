"""
@Project ：Titan
@File    ：all.py
@Author  ：PySuper
@Date    ：2025/4/29 14:25
@Desc    ：Titan all.py
"""

import base64
import datetime
import gzip
import hashlib
import json
import math
import os
import pickle
import random
import re
import string
import time
import zlib
from typing import Any, Dict, List, Union, Optional, Tuple


# ======================== 时间工具 ========================
class TimeUtils:
    @staticmethod
    def get_timestamp() -> int:
        """获取当前时间戳（秒）"""
        return int(time.time())

    @staticmethod
    def get_timestamp_ms() -> int:
        """获取当前时间戳（毫秒）"""
        return int(time.time() * 1000)

    @staticmethod
    def timestamp_to_datetime(timestamp: int) -> datetime.datetime:
        """时间戳转datetime对象"""
        return datetime.datetime.fromtimestamp(timestamp)

    @staticmethod
    def datetime_to_timestamp(dt: datetime.datetime) -> int:
        """datetime对象转时间戳"""
        return int(dt.timestamp())

    @staticmethod
    def format_datetime(dt: Optional[datetime.datetime] = None, fmt: str = "%Y-%m-%d %H:%M:%S") -> str:
        """格式化datetime对象为字符串"""
        if dt is None:
            dt = datetime.datetime.now()
        return dt.strftime(fmt)

    @staticmethod
    def parse_datetime(date_str: str, fmt: str = "%Y-%m-%d %H:%M:%S") -> datetime.datetime:
        """解析字符串为datetime对象"""
        return datetime.datetime.strptime(date_str, fmt)

    @staticmethod
    def get_date_range(start_date: str, end_date: str, fmt: str = "%Y-%m-%d") -> List[str]:
        """获取日期范围列表"""
        start = TimeUtils.parse_datetime(start_date, fmt)
        end = TimeUtils.parse_datetime(end_date, fmt)

        date_list = []
        current = start
        while current <= end:
            date_list.append(current.strftime(fmt))
            current += datetime.timedelta(days=1)

        return date_list


# ======================== 加密工具 ========================
class EncryptUtils:
    @staticmethod
    def md5(text: str) -> str:
        """MD5加密"""
        return hashlib.md5(text.encode("utf-8")).hexdigest()

    @staticmethod
    def sha1(text: str) -> str:
        """SHA1加密"""
        return hashlib.sha1(text.encode("utf-8")).hexdigest()

    @staticmethod
    def sha256(text: str) -> str:
        """SHA256加密"""
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    @staticmethod
    def base64_encode(text: str) -> str:
        """Base64编码"""
        return base64.b64encode(text.encode("utf-8")).decode("utf-8")

    @staticmethod
    def hmac_sha256(key: str, message: str) -> str:
        """HMAC-SHA256加密"""
        import hmac

        return hmac.new(key.encode("utf-8"), message.encode("utf-8"), hashlib.sha256).hexdigest()


# ======================== 解密工具 ========================
class DecryptUtils:
    @staticmethod
    def base64_decode(encoded_text: str) -> str:
        """Base64解码"""
        return base64.b64decode(encoded_text.encode("utf-8")).decode("utf-8")

    @staticmethod
    def verify_md5(text: str, md5_hash: str) -> bool:
        """验证MD5哈希"""
        return EncryptUtils.md5(text) == md5_hash

    @staticmethod
    def verify_sha1(text: str, sha1_hash: str) -> bool:
        """验证SHA1哈希"""
        return EncryptUtils.sha1(text) == sha1_hash

    @staticmethod
    def verify_sha256(text: str, sha256_hash: str) -> bool:
        """验证SHA256哈希"""
        return EncryptUtils.sha256(text) == sha256_hash


# ======================== 压缩工具 ========================
class CompressUtils:
    @staticmethod
    def zlib_compress(data: Union[str, bytes]) -> bytes:
        """使用zlib压缩数据"""
        if isinstance(data, str):
            data = data.encode("utf-8")
        return zlib.compress(data)

    @staticmethod
    def gzip_compress(data: Union[str, bytes]) -> bytes:
        """使用gzip压缩数据"""
        if isinstance(data, str):
            data = data.encode("utf-8")
        return gzip.compress(data)

    @staticmethod
    def compress_file(file_path: str, output_path: Optional[str] = None) -> str:
        """压缩文件"""
        import shutil

        if output_path is None:
            output_path = f"{file_path}.gz"

        with open(file_path, "rb") as f_in:
            with gzip.open(output_path, "wb") as f_out:
                shutil.copyfileobj(f_in, f_out)

        return output_path


# ======================== 解压缩工具 ========================
class DecompressUtils:
    @staticmethod
    def zlib_decompress(compressed_data: bytes) -> bytes:
        """使用zlib解压数据"""
        return zlib.decompress(compressed_data)

    @staticmethod
    def gzip_decompress(compressed_data: bytes) -> bytes:
        """使用gzip解压数据"""
        return gzip.decompress(compressed_data)

    @staticmethod
    def decompress_file(compressed_file: str, output_path: Optional[str] = None) -> str:
        """解压文件"""
        import shutil

        if output_path is None:
            output_path = compressed_file.replace(".gz", "")

        with gzip.open(compressed_file, "rb") as f_in:
            with open(output_path, "wb") as f_out:
                shutil.copyfileobj(f_in, f_out)

        return output_path


# ======================== 序列化工具 ========================
class SerializeUtils:
    @staticmethod
    def to_json(obj: Any) -> str:
        """将对象序列化为JSON字符串"""
        return json.dumps(obj, ensure_ascii=False)

    @staticmethod
    def to_pickle(obj: Any) -> bytes:
        """将对象序列化为pickle字节流"""
        return pickle.dumps(obj)

    @staticmethod
    def to_base64(obj: Any) -> str:
        """将对象序列化为base64字符串"""
        return base64.b64encode(pickle.dumps(obj)).decode("utf-8")

    @staticmethod
    def object_to_dict(obj: Any) -> Dict:
        """将对象转换为字典"""
        if hasattr(obj, "__dict__"):
            return obj.__dict__
        elif hasattr(obj, "_asdict"):  # namedtuple
            return obj._asdict()
        else:
            return obj


# ======================== 反序列化工具 ========================
class DeserializeUtils:
    @staticmethod
    def from_json(json_str: str) -> Any:
        """从JSON字符串反序列化对象"""
        return json.loads(json_str)

    @staticmethod
    def from_pickle(pickle_bytes: bytes) -> Any:
        """从pickle字节流反序列化对象"""
        return pickle.loads(pickle_bytes)

    @staticmethod
    def from_base64(base64_str: str) -> Any:
        """从base64字符串反序列化对象"""
        return pickle.loads(base64.b64decode(base64_str.encode("utf-8")))

    @staticmethod
    def dict_to_object(dict_data: Dict, cls: Any) -> Any:
        """将字典转换为对象"""
        obj = cls()
        for key, value in dict_data.items():
            setattr(obj, key, value)
        return obj


# ======================== 验证工具 ========================
class ValidateUtils:
    @staticmethod
    def is_email(email: str) -> bool:
        """验证是否为有效的电子邮件地址"""
        pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        return bool(re.match(pattern, email))

    @staticmethod
    def is_phone_number(phone: str) -> bool:
        """验证是否为有效的手机号码（中国）"""
        pattern = r"^1[3-9]\d{9}$"
        return bool(re.match(pattern, phone))

    @staticmethod
    def is_url(url: str) -> bool:
        """验证是否为有效的URL"""
        pattern = r"^(https?|ftp)://[^\s/$.?#].[^\s]*$"
        return bool(re.match(pattern, url))

    @staticmethod
    def is_ip_address(ip: str) -> bool:
        """验证是否为有效的IP地址"""
        pattern = r"^(\d{1,3}\.){3}\d{1,3}$"
        if not re.match(pattern, ip):
            return False

        # 验证每个部分是否在0-255范围内
        parts = ip.split(".")
        return all(0 <= int(part) <= 255 for part in parts)

    @staticmethod
    def is_chinese_id_card(id_card: str) -> bool:
        """验证是否为有效的中国身份证号码"""
        # 18位身份证号码验证
        if len(id_card) == 18:
            pattern = r"^\d{17}[\dXx]$"
            return bool(re.match(pattern, id_card))
        # 15位身份证号码验证
        elif len(id_card) == 15:
            pattern = r"^\d{15}$"
            return bool(re.match(pattern, id_card))
        return False


# ======================== 转换工具 ========================
class ConvertUtils:
    @staticmethod
    def str_to_int(s: str, default: int = 0) -> int:
        """字符串转整数，失败返回默认值"""
        try:
            return int(s)
        except (ValueError, TypeError):
            return default

    @staticmethod
    def str_to_float(s: str, default: float = 0.0) -> float:
        """字符串转浮点数，失败返回默认值"""
        try:
            return float(s)
        except (ValueError, TypeError):
            return default

    @staticmethod
    def str_to_bool(s: str) -> bool:
        """字符串转布尔值"""
        return s.lower() in ("true", "yes", "1", "t", "y")

    @staticmethod
    def bytes_to_str(b: bytes, encoding: str = "utf-8") -> str:
        """字节转字符串"""
        return b.decode(encoding)

    @staticmethod
    def str_to_bytes(s: str, encoding: str = "utf-8") -> bytes:
        """字符串转字节"""
        return s.encode(encoding)

    @staticmethod
    def list_to_tuple(lst: List) -> Tuple:
        """列表转元组"""
        return tuple(lst)

    @staticmethod
    def tuple_to_list(tpl: Tuple) -> List:
        """元组转列表"""
        return list(tpl)


# ======================== 格式化工具 ========================
class FormatUtils:
    @staticmethod
    def format_number(num: Union[int, float], decimal_places: int = 2) -> str:
        """格式化数字，保留指定小数位"""
        return f"{num:.{decimal_places}f}"

    @staticmethod
    def format_currency(amount: Union[int, float], symbol: str = "¥", decimal_places: int = 2) -> str:
        """格式化货币"""
        return f"{symbol}{amount:.{decimal_places}f}"

    @staticmethod
    def format_file_size(size_bytes: int) -> str:
        """格式化文件大小"""
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.2f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.2f} MB"
        else:
            return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"

    @staticmethod
    def format_percent(value: float, total: float, decimal_places: int = 2) -> str:
        """格式化百分比"""
        if total == 0:
            return "0%"
        percentage = (value / total) * 100
        return f"{percentage:.{decimal_places}f}%"

    @staticmethod
    def format_phone(phone: str) -> str:
        """格式化手机号码（隐藏中间4位）"""
        if len(phone) != 11:
            return phone
        return f"{phone[:3]}****{phone[7:]}"


# ======================== 解析工具 ========================
class ParseUtils:
    @staticmethod
    def parse_url(url: str) -> Dict[str, str]:
        """解析URL"""
        from urllib.parse import urlparse, parse_qs

        parsed_url = urlparse(url)
        query_params = parse_qs(parsed_url.query)

        # 将列表值转换为单个值
        for key, value in query_params.items():
            if isinstance(value, list) and len(value) == 1:
                query_params[key] = value[0]

        return {
            "scheme": parsed_url.scheme,
            "netloc": parsed_url.netloc,
            "path": parsed_url.path,
            "params": parsed_url.params,
            "query": query_params,
            "fragment": parsed_url.fragment,
        }

    @staticmethod
    def parse_json(json_str: str) -> Dict:
        """解析JSON字符串"""
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            return {}

    @staticmethod
    def parse_xml(xml_str: str) -> Dict:
        """解析XML字符串"""
        import xml.etree.ElementTree as ET

        try:
            root = ET.fromstring(xml_str)
            result = {}

            def _parse_element(element, result_dict):
                if len(element) == 0:
                    result_dict[element.tag] = element.text
                else:
                    result_dict[element.tag] = {}
                    for child in element:
                        _parse_element(child, result_dict[element.tag])

            for child in root:
                _parse_element(child, result)

            return result
        except Exception:
            return {}

    @staticmethod
    def parse_csv(csv_str: str, delimiter: str = ",") -> List[Dict]:
        """解析CSV字符串"""
        import csv
        from io import StringIO

        result = []
        try:
            csv_file = StringIO(csv_str)
            reader = csv.DictReader(csv_file, delimiter=delimiter)
            for row in reader:
                result.append(dict(row))
            return result
        except Exception:
            return []


# ======================== 生成工具 ========================
class GenerateUtils:
    @staticmethod
    def generate_random_string(length: int = 8) -> str:
        """生成随机字符串"""
        chars = string.ascii_letters + string.digits
        return "".join(random.choice(chars) for _ in range(length))

    @staticmethod
    def generate_random_number(min_value: int = 0, max_value: int = 100) -> int:
        """生成随机整数"""
        return random.randint(min_value, max_value)

    @staticmethod
    def generate_uuid() -> str:
        """生成UUID"""
        import uuid

        return str(uuid.uuid4())

    @staticmethod
    def generate_password(length: int = 12, include_special: bool = True) -> str:
        """生成强密码"""
        chars = string.ascii_lowercase + string.ascii_uppercase + string.digits
        if include_special:
            chars += "!@#$%^&*()_+-=[]{}|;:,.<>?"

        # 确保密码包含至少一个小写字母、一个大写字母、一个数字和一个特殊字符
        password = [
            random.choice(string.ascii_lowercase),
            random.choice(string.ascii_uppercase),
            random.choice(string.digits),
        ]

        if include_special:
            password.append(random.choice("!@#$%^&*()_+-=[]{}|;:,.<>?"))

        # 填充剩余长度
        password.extend(random.choice(chars) for _ in range(length - len(password)))

        # 打乱顺序
        random.shuffle(password)

        return "".join(password)

    @staticmethod
    def generate_verification_code(length: int = 6) -> str:
        """生成数字验证码"""
        return "".join(random.choice(string.digits) for _ in range(length))


# ======================== 计算工具 ========================
class CalculateUtils:
    @staticmethod
    def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """计算两点之间的距离（单位：公里）"""
        # 地球半径（公里）
        R = 6371.0

        # 将经纬度转换为弧度
        lat1_rad = math.radians(lat1)
        lon1_rad = math.radians(lon1)
        lat2_rad = math.radians(lat2)
        lon2_rad = math.radians(lon2)

        # 经纬度差值
        dlon = lon2_rad - lon1_rad
        dlat = lat2_rad - lat1_rad

        # Haversine公式
        a = math.sin(dlat / 2) ** 2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2) ** 2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        distance = R * c

        return distance

    @staticmethod
    def calculate_average(numbers: List[Union[int, float]]) -> float:
        """计算平均值"""
        if not numbers:
            return 0.0
        return sum(numbers) / len(numbers)

    @staticmethod
    def calculate_median(numbers: List[Union[int, float]]) -> float:
        """计算中位数"""
        if not numbers:
            return 0.0

        sorted_numbers = sorted(numbers)
        n = len(sorted_numbers)

        if n % 2 == 0:
            # 偶数个元素，取中间两个的平均值
            return (sorted_numbers[n // 2 - 1] + sorted_numbers[n // 2]) / 2
        else:
            # 奇数个元素，取中间值
            return sorted_numbers[n // 2]

    @staticmethod
    def calculate_variance(numbers: List[Union[int, float]]) -> float:
        """计算方差"""
        if not numbers or len(numbers) < 2:
            return 0.0

        avg = CalculateUtils.calculate_average(numbers)
        return sum((x - avg) ** 2 for x in numbers) / len(numbers)

    @staticmethod
    def calculate_standard_deviation(numbers: List[Union[int, float]]) -> float:
        """计算标准差"""
        return math.sqrt(CalculateUtils.calculate_variance(numbers))


# ======================== 存储工具 ========================
class StorageUtils:
    @staticmethod
    def save_to_file(data: Union[str, bytes], file_path: str, mode: str = "w") -> bool:
        """保存数据到文件"""
        try:
            with open(file_path, mode) as f:
                f.write(data)
            return True
        except Exception:
            return False

    @staticmethod
    def read_from_file(file_path: str, mode: str = "r") -> Union[str, bytes, None]:
        """从文件读取数据"""
        try:
            with open(file_path, mode) as f:
                return f.read()
        except Exception:
            return None

    @staticmethod
    def append_to_file(data: Union[str, bytes], file_path: str, mode: str = "a") -> bool:
        """追加数据到文件"""
        try:
            with open(file_path, mode) as f:
                f.write(data)
            return True
        except Exception:
            return False

    @staticmethod
    def save_json(data: Any, file_path: str) -> bool:
        """保存JSON数据到文件"""
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception:
            return False

    @staticmethod
    def load_json(file_path: str) -> Any:
        """从文件加载JSON数据"""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None

    @staticmethod
    def save_pickle(data: Any, file_path: str) -> bool:
        """保存对象到pickle文件"""
        try:
            with open(file_path, "wb") as f:
                pickle.dump(data, f)
            return True
        except Exception:
            return False

    @staticmethod
    def load_pickle(file_path: str) -> Any:
        """从pickle文件加载对象"""
        try:
            with open(file_path, "rb") as f:
                return pickle.load(f)
        except Exception:
            return None

    @staticmethod
    def get_file_size(file_path: str) -> int:
        """获取文件大小（字节）"""
        try:
            return os.path.getsize(file_path)
        except Exception:
            return 0

    @staticmethod
    def ensure_dir(directory: str) -> bool:
        """确保目录存在，不存在则创建"""
        try:
            if not os.path.exists(directory):
                os.makedirs(directory)
            return True
        except Exception:
            return False
