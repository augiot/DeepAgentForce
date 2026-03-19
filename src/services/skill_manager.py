"""
Skill 管理服务
负责动态加载、卸载、验证前端上传的 Skill
支持 Skill 的即插即用
"""

import logging
import shutil
import uuid
import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class SkillManager:
    """Skill 管理器 - 支持前端动态上传 Skill"""
    
    def __init__(self, skills_dir: Path):
        self.skills_dir = Path(skills_dir)
        self.skills_dir.mkdir(parents=True, exist_ok=True)
        self._skills_cache: Dict[str, Dict[str, Any]] = {}
    
    def list_skills(self) -> List[Dict[str, Any]]:
        """列出所有已安装的 Skills"""
        skills = []
        
        for skill_path in self.skills_dir.iterdir():
            if not skill_path.is_dir():
                continue
            
            skill_info = self._parse_skill_info(skill_path)
            if skill_info:
                skills.append(skill_info)
        
        # 按名称排序
        skills.sort(key=lambda x: x.get('name', ''))
        return skills
    
    def _parse_skill_info(self, skill_path: Path) -> Optional[Dict[str, Any]]:
        """解析 Skill 目录，提取元信息"""
        skill_md = skill_path / "SKILL.md"
        
        if not skill_md.exists():
            return None
        
        try:
            # 读取 SKILL.md 解析 frontmatter
            content = skill_md.read_text(encoding='utf-8')
            metadata = self._extract_frontmatter(content)
            
            # 获取 scripts 目录信息
            scripts_dir = skill_path / "scripts"
            scripts = []
            if scripts_dir.exists():
                for script_file in scripts_dir.iterdir():
                    if script_file.is_file() and script_file.suffix == '.py':
                        scripts.append({
                            'name': script_file.stem,
                            'file': script_file.name,
                            'path': str(script_file.relative_to(self.skills_dir.parent.parent))
                        })
            
            # 统计信息
            created_at = datetime.fromtimestamp(skill_path.stat().st_ctime).isoformat()
            modified_at = datetime.fromtimestamp(skill_path.stat().st_mtime).isoformat()
            
            return {
                'id': skill_path.name,
                'name': metadata.get('name', skill_path.name),
                'description': metadata.get('description', ''),
                'version': metadata.get('version', '1.0.0'),
                'author': metadata.get('author', 'Unknown'),
                'tags': metadata.get('tags', []),
                'path': str(skill_path),
                'scripts': scripts,
                'script_count': len(scripts),
                'created_at': created_at,
                'modified_at': modified_at
            }
        except Exception as e:
            logger.error(f"解析 Skill 失败 {skill_path}: {e}")
            return None
    
    def _extract_frontmatter(self, content: str) -> Dict[str, Any]:
        """提取 YAML frontmatter"""
        metadata = {}
        
        if content.startswith('---'):
            lines = content.split('\n')
            in_frontmatter = False
            key_buffer = []
            value_buffer = []
            current_key = None
            
            for i, line in enumerate(lines[1:], 1):
                if line.strip() == '---':
                    if not in_frontmatter:
                        in_frontmatter = True
                        continue
                    else:
                        break
                
                if in_frontmatter and ':' in line:
                    # 处理多行值
                    if line.startswith(' ') or line.startswith('\t'):
                        if current_key:
                            value_buffer.append(line.strip())
                    else:
                        # 保存前一个 key-value
                        if current_key:
                            key = current_key.strip()
                            value = ':'.join(value_buffer).strip()
                            # 处理列表
                            if value.startswith('[') and value.endswith(']'):
                                value = [v.strip().strip('"\'') for v in value[1:-1].split(',')]
                            metadata[key] = value
                        
                        # 开始新的 key
                        idx = line.index(':')
                        current_key = line[:idx]
                        value_buffer = [line[idx+1:].strip()]
            
            # 保存最后一个 key-value
            if current_key:
                key = current_key.strip()
                value = ':'.join(value_buffer).strip()
                if value.startswith('[') and value.endswith(']'):
                    value = [v.strip().strip('"\'') for v in value[1:-1].split(',')]
                metadata[key] = value
        
        return metadata
    
    def get_skill(self, skill_id: str) -> Optional[Dict[str, Any]]:
        """获取指定 Skill 的详细信息"""
        skill_path = self.skills_dir / skill_id
        
        if not skill_path.exists():
            return None
        
        return self._parse_skill_info(skill_path)
    
    def get_skill_content(self, skill_id: str) -> Optional[Dict[str, str]]:
        """获取 Skill 文件内容 (SKILL.md 和 scripts)"""
        skill_path = self.skills_dir / skill_id
        
        if not skill_path.exists():
            return None
        
        result = {}
        
        # 读取 SKILL.md
        skill_md = skill_path / "SKILL.md"
        if skill_md.exists():
            result['SKILL.md'] = skill_md.read_text(encoding='utf-8')
        
        # 读取 scripts
        scripts_dir = skill_path / "scripts"
        if scripts_dir.exists():
            result['scripts'] = {}
            for script_file in scripts_dir.iterdir():
                if script_file.is_file():
                    result['scripts'][script_file.name] = script_file.read_text(encoding='utf-8')
        
        return result
    
    def validate_skill(self, skill_md_content: str, scripts: Dict[str, str]) -> Dict[str, Any]:
        """验证 Skill 规范的合法性"""
        errors = []
        warnings = []
        
        # 1. 验证 SKILL.md
        if not skill_md_content.strip():
            errors.append("SKILL.md 内容不能为空")
        else:
            metadata = self._extract_frontmatter(skill_md_content)
            
            if not metadata.get('name'):
                errors.append("SKILL.md 缺少 name 字段")
            
            if not metadata.get('description'):
                warnings.append("建议添加 description 字段")
        
        # 2. 验证 scripts
        if not scripts:
            warnings.append("建议至少提供一个脚本")
        else:
            for script_name, content in scripts.items():
                if not content.strip():
                    errors.append(f"脚本 {script_name} 内容为空")
                # 检查是否是有效的 Python 文件
                if script_name.endswith('.py'):
                    try:
                        compile(content, script_name, 'exec')
                    except SyntaxError as e:
                        warnings.append(f"脚本 {script_name} 存在语法问题: {e}")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings
        }
    
    def install_skill(
        self,
        skill_name: str,
        skill_md_content: str,
        scripts: Dict[str, str],
        force: bool = False
    ) -> Dict[str, Any]:
        """安装/更新 Skill"""
        
        # 验证合法性
        validation = self.validate_skill(skill_md_content, scripts)
        
        if not validation['valid']:
            return {
                'success': False,
                'message': '验证失败',
                'errors': validation['errors']
            }
        
        # 生成 Skill ID
        skill_id = self._generate_skill_id(skill_name)
        skill_path = self.skills_dir / skill_id
        
        # 检查是否已存在
        if skill_path.exists() and not force:
            return {
                'success': False,
                'message': f"Skill '{skill_name}' 已存在，请使用更新接口"
            }
        
        try:
            # 创建目录结构
            if skill_path.exists():
                shutil.rmtree(skill_path)
            
            skill_path.mkdir(parents=True, exist_ok=True)
            scripts_dir = skill_path / "scripts"
            scripts_dir.mkdir(parents=True, exist_ok=True)
            
            # 写入 SKILL.md
            (skill_path / "SKILL.md").write_text(skill_md_content, encoding='utf-8')
            
            # 写入 scripts
            for script_name, content in scripts.items():
                script_path = scripts_dir / script_name
                script_path.write_text(content, encoding='utf-8')
            
            # 清除缓存
            self._skills_cache.clear()
            
            return {
                'success': True,
                'message': f"Skill '{skill_name}' 安装成功",
                'skill_id': skill_id,
                'warnings': validation['warnings']
            }
            
        except Exception as e:
            logger.error(f"安装 Skill 失败: {e}")
            # 清理失败的文件
            if skill_path.exists():
                shutil.rmtree(skill_path)
            
            return {
                'success': False,
                'message': f"安装失败: {str(e)}"
            }
    
    def _generate_skill_id(self, skill_name: str) -> str:
        """从 Skill 名称生成 ID"""
        # 转换为小写，替换空格和特殊字符为连字符
        import re
        skill_id = skill_name.lower()
        skill_id = re.sub(r'[^a-z0-9]+', '-', skill_id)
        skill_id = skill_id.strip('-')
        return skill_id
    
    def uninstall_skill(self, skill_id: str) -> Dict[str, Any]:
        """卸载 Skill"""
        skill_path = self.skills_dir / skill_id
        
        if not skill_path.exists():
            return {
                'success': False,
                'message': f"Skill '{skill_id}' 不存在"
            }
        
        # 检查是否是内置 Skill (不允许删除)
        builtin_skills = {'pdf-processing', 'rag-query', 'web-search'}
        if skill_id in builtin_skills:
            return {
                'success': False,
                'message': "内置 Skill 不能删除"
            }
        
        try:
            shutil.rmtree(skill_path)
            self._skills_cache.clear()
            
            return {
                'success': True,
                'message': f"Skill '{skill_id}' 已卸载"
            }
        except Exception as e:
            return {
                'success': False,
                'message': f"卸载失败: {str(e)}"
            }
    
    def export_skill(self, skill_id: str) -> Optional[Dict[str, Any]]:
        """导出 Skill 为可分享的格式"""
        skill_path = self.skills_dir / skill_id
        
        if not skill_path.exists():
            return None
        
        content = self.get_skill_content(skill_id)
        if not content:
            return None
        
        # 构建导出结构
        skill_md = content.pop('SKILL.md', '')
        scripts = content.pop('scripts', {})
        
        return {
            'skill_md': skill_md,
            'scripts': scripts,
            'exported_at': datetime.now().isoformat()
        }
    
    def get_skill_template(self) -> Dict[str, Any]:
        """获取 Skill 模板"""
        return {
            'skill_md': '''---
name: my-custom-skill
description: A custom skill for specific tasks
version: 1.0.0
author: Your Name
tags:
  - custom
  - utility
---

# My Custom Skill

## When to use this skill

Use this skill when the user wants to:
- Do something specific
- Solve a particular problem

## Available Scripts

### 1. Main Script: `main.py`

**When to use**: Always

**Usage**:
```bash
python src/services/skills/my-custom-skill/scripts/main.py --param1 value1
```

**Parameters**:
- `--param1`: Description of param1

**Example**:
```bash
python src/services/skills/my-custom-skill/scripts/main.py --param1 hello
```
''',
            'scripts': {
                'main.py': '''#!/usr/bin/env python3
"""
Custom Skill Main Script
"""
import argparse
import sys

def main():
    parser = argparse.ArgumentParser(description="Custom skill script")
    parser.add_argument('--param1', type=str, default='default', help='Parameter 1')
    args = parser.parse_args()
    
    # Your logic here
    print(f"Hello, {args.param1}!")
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
'''
            }
        }
