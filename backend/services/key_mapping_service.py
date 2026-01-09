"""
Key-目标服务器映射服务

负责管理 API Key 到目标服务器地址的映射关系
"""

import json
import os
from typing import Dict, List, Optional
from pydantic import BaseModel


class TargetMapping(BaseModel):
    """单个目标服务器映射"""
    target_url: str
    keys: List[str] = []


class KeyMappingsData(BaseModel):
    """完整的映射数据"""
    mappings: List[TargetMapping] = []


class KeyMappingService:
    """Key-目标服务器映射服务"""

    def __init__(self, mappings_file: str = "env/.env.key-mappings.json"):
        self.mappings_file = mappings_file

    def load_mappings(self) -> KeyMappingsData:
        """加载映射配置"""
        if not os.path.exists(self.mappings_file):
            return KeyMappingsData(mappings=[])

        try:
            with open(self.mappings_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            mappings = []
            for item in data.get("mappings", []):
                mappings.append(TargetMapping(
                    target_url=item.get("target_url", ""),
                    keys=item.get("keys", [])
                ))
            return KeyMappingsData(mappings=mappings)

        except (json.JSONDecodeError, Exception) as e:
            print(f"[KeyMappingService] Failed to load mappings: {e}")
            return KeyMappingsData(mappings=[])

    def save_mappings(self, data: KeyMappingsData) -> bool:
        """保存映射配置"""
        try:
            os.makedirs(os.path.dirname(self.mappings_file), exist_ok=True)

            with open(self.mappings_file, 'w', encoding='utf-8') as f:
                json.dump(data.model_dump(), f, ensure_ascii=False, indent=2)

            print(f"[KeyMappingService] Saved {len(data.mappings)} mappings to {self.mappings_file}")
            return True

        except Exception as e:
            print(f"[KeyMappingService] Failed to save mappings: {e}")
            return False

    def get_all_mappings(self) -> List[TargetMapping]:
        """获取所有映射"""
        return self.load_mappings().mappings

    def add_target(self, target_url: str, keys: List[str] = None) -> bool:
        """添加目标服务器"""
        data = self.load_mappings()

        for mapping in data.mappings:
            if mapping.target_url == target_url:
                print(f"[KeyMappingService] Target {target_url} already exists")
                return False

        data.mappings.append(TargetMapping(
            target_url=target_url,
            keys=keys or []
        ))

        return self.save_mappings(data)

    def remove_target(self, target_url: str) -> bool:
        """删除目标服务器"""
        data = self.load_mappings()

        original_count = len(data.mappings)
        data.mappings = [m for m in data.mappings if m.target_url != target_url]

        if len(data.mappings) == original_count:
            print(f"[KeyMappingService] Target {target_url} not found")
            return False

        return self.save_mappings(data)

    def update_target(self, target_url: str, new_target_url: str = None, keys: List[str] = None) -> bool:
        """更新目标服务器配置"""
        data = self.load_mappings()

        for mapping in data.mappings:
            if mapping.target_url == target_url:
                if new_target_url:
                    mapping.target_url = new_target_url
                if keys is not None:
                    mapping.keys = keys
                return self.save_mappings(data)

        print(f"[KeyMappingService] Target {target_url} not found")
        return False

    def add_key_to_target(self, target_url: str, key: str) -> bool:
        """向目标服务器添加 key"""
        data = self.load_mappings()

        for mapping in data.mappings:
            if mapping.target_url == target_url:
                if key not in mapping.keys:
                    mapping.keys.append(key)
                    return self.save_mappings(data)
                return True

        print(f"[KeyMappingService] Target {target_url} not found")
        return False

    def remove_key_from_target(self, target_url: str, key: str) -> bool:
        """从目标服务器删除 key"""
        data = self.load_mappings()

        for mapping in data.mappings:
            if mapping.target_url == target_url:
                if key in mapping.keys:
                    mapping.keys.remove(key)
                    return self.save_mappings(data)
                return True

        print(f"[KeyMappingService] Target {target_url} not found")
        return False

    def find_target_by_key(self, key: str, default_target: str = None) -> Optional[str]:
        """根据 key 查找对应的目标服务器"""
        data = self.load_mappings()

        for mapping in data.mappings:
            if key in mapping.keys:
                return mapping.target_url

        return default_target

    def build_key_index(self) -> Dict[str, str]:
        """构建 key -> target_url 的索引"""
        data = self.load_mappings()
        index = {}

        for mapping in data.mappings:
            for key in mapping.keys:
                index[key] = mapping.target_url

        return index

    def reload_config_module(self):
        """重新加载 config 模块中的映射数据"""
        from .. import config as config_module

        config_module.KEY_TARGET_MAPPINGS = config_module.load_key_target_mappings()
        config_module.KEY_TO_TARGET_INDEX = config_module.build_key_to_target_index(
            config_module.KEY_TARGET_MAPPINGS
        )
        print(f"[KeyMappingService] Reloaded config module, {len(config_module.KEY_TO_TARGET_INDEX)} keys indexed")


key_mapping_service = KeyMappingService()
