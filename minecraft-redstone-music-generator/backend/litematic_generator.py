"""
投影文件生成模块 - 增强版
支持多种Minecraft结构格式：
1. Schematic (MCEdit/WorldEdit)
2. Litematic (Litematica)
3. Structure Block (NBT结构方块)
4. 蓝图文件 (Blueprint)
"""

import struct
import zlib
import json
import numpy as np
from collections import defaultdict
import io
import os
import nbtlib
from nbtlib import Compound, List, String, Int, Byte, Short, Long, Float, Double

class LitematicGenerator:
    def __init__(self):
        # 方块ID映射 - 扩展更多方块
        self.block_ids = {
            'air': 0,
            'stone': 1,
            'grass': 2,
            'dirt': 3,
            'cobblestone': 4,
            'planks': 5,
            'note_block': 25,
            'redstone_wire': 55,
            'repeater': 93,
            'redstone_block': 152,
            'lever': 69,
            'sticky_piston': 29,
            'slime_block': 165,
            'oak_planks': 5,
            'glass': 20,
            'torch': 50,
            'redstone_torch': 76,
            'dispenser': 23,
            'dropper': 158,
            'observer': 251,
            'piston': 33,
            'sticky_piston_head': 34,
            'quartz_block': 155,
            'iron_block': 42,
            'gold_block': 41,
            'diamond_block': 57,
            'emerald_block': 133,
            'lapis_block': 22,
            'coal_block': 173,
            'hay_block': 170,
            'bookshelf': 47,
            'jukebox': 84,
            'tnt': 46,
            'beacon': 138,
            'command_block': 137,
            'structure_block': 255,
            'barrier': 166,
            'light_block': 125
        }
        
        # 方块状态映射
        self.block_states = {
            'repeater': {
                0: {'facing': 'south', 'delay': '1', 'locked': 'false', 'powered': 'false'},
                1: {'facing': 'west', 'delay': '1', 'locked': 'false', 'powered': 'false'},
                2: {'facing': 'north', 'delay': '1', 'locked': 'false', 'powered': 'false'},
                3: {'facing': 'east', 'delay': '1', 'locked': 'false', 'powered': 'false'}
            },
            'note_block': {
                'instrument': 'harp',
                'note': '0',
                'powered': 'false'
            }
        }
        
        print("[投影生成器] 增强版初始化完成，支持多种格式")
    
    def generate_projection(self, redstone_notes, output_path, format_type='schematic', config=None):
        """
        生成投影文件 - 统一接口
        
        参数:
            redstone_notes: 红石音符列表
            output_path: 输出文件路径
            format_type: 格式类型 ('schematic', 'litematic', 'structure', 'blueprint')
            config: 配置字典
            
        返回:
            生成统计信息
        """
        if config is None:
            config = {}
        
        print(f"[投影生成] 格式: {format_type}, 配置: {config}")
        
        # 计算尺寸
        max_time = max([note['time_ticks'] for note in redstone_notes]) if redstone_notes else 0
        width = min(max(max_time // 5 + 5, 10), 128)
        height = min(config.get('height', 6), 64)
        length = min(max(len(redstone_notes) // 5 + 5, 8), 128)
        
        name = config.get('name', f"RedstoneMusic_{os.path.basename(output_path).split('.')[0]}")
        
        # 根据格式调用相应方法
        if format_type == 'schematic':
            file_path = output_path if output_path.endswith('.schematic') else output_path + '.schematic'
            success = self.generate_schematic(redstone_notes, file_path, config)
        elif format_type == 'litematic':
            file_path = output_path if output_path.endswith('.litematic') else output_path + '.litematic'
            success = self.generate_litematic(redstone_notes, file_path, config)
        elif format_type == 'structure':
            file_path = output_path if output_path.endswith('.nbt') else output_path + '.nbt'
            success = self.generate_structure_nbt(redstone_notes, file_path, config)
        elif format_type == 'blueprint':
            file_path = output_path if output_path.endswith('.json') else output_path + '.json'
            success = self.generate_blueprint(redstone_notes, file_path, config)
        else:
            print(f"[错误] 不支持的格式: {format_type}")
            return self._create_default_stats(name, width, height, length)
        
        if not success:
            print(f"[警告] {format_type} 生成可能有问题")
        
        # 计算文件大小
        file_size = os.path.getsize(file_path) // 1024 if os.path.exists(file_path) else 0
        
        return {
            'name': name,
            'dimensions': {'width': width, 'height': height, 'length': length},
            'note_blocks': len(redstone_notes),
            'redstone_dust': len(redstone_notes),
            'repeaters': max(len(redstone_notes) // 10, 1),
            'redstone_length': max_time,
            'duration': max_time / 10.0,
            'file_size': file_size,
            'format': format_type,
            'file_path': file_path
        }
    
    def generate_schematic(self, redstone_notes, output_path, config=None):
        """
        生成Schematic文件 (MCEdit/WorldEdit格式)
        """
        try:
            print(f"[Schematic] 生成: {output_path}")
            
            # 获取配置
            if config is None:
                config = {}
            
            version = config.get('schematic_version', 2)
            include_entities = config.get('include_entities', False)
            include_tile_entities = config.get('include_tile_entities', True)
            
            # 创建Schematic
            schematic_data = self._create_schematic_data(redstone_notes, config)
            
            with open(output_path, 'wb') as f:
                f.write(schematic_data)
            
            print(f"[Schematic] 完成: {output_path} ({os.path.getsize(output_path)} 字节)")
            return True
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"[Schematic错误] 生成失败: {str(e)}")
            return False
    
    def generate_litematic(self, redstone_notes, output_path, config=None):
        """
        生成Litematic文件 (Litematica格式)
        """
        try:
            print(f"[Litematic] 生成: {output_path}")
            
            if config is None:
                config = {}
            
            # 创建Litematic结构
            litematic_data = self._create_litematic_data(redstone_notes, config)
            
            # 保存为gzip压缩的NBT文件
            import gzip
            with gzip.open(output_path, 'wb') as f:
                f.write(litematic_data)
            
            print(f"[Litematic] 完成: {output_path} ({os.path.getsize(output_path)} 字节)")
            return True
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"[Litematic错误] 生成失败: {str(e)}")
            # 回退到Schematic
            return self.generate_schematic(redstone_notes, output_path, config)
    
    def generate_structure_nbt(self, redstone_notes, output_path, config=None):
        """
        生成结构方块NBT文件 (Minecraft结构方块格式)
        """
        try:
            print(f"[Structure NBT] 生成: {output_path}")
            
            if config is None:
                config = {}
            
            # 创建NBT结构
            nbt_structure = self._create_structure_nbt(redstone_notes, config)
            
            # 保存NBT文件
            nbt_structure.save(output_path, gzipped=True)
            
            print(f"[Structure NBT] 完成: {output_path} ({os.path.getsize(output_path)} 字节)")
            return True
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"[Structure NBT错误] 生成失败: {str(e)}")
            return False
    
    def generate_blueprint(self, redstone_notes, output_path, config=None):
        """
        生成蓝图文件 (JSON格式，兼容多种工具)
        """
        try:
            print(f"[Blueprint] 生成: {output_path}")
            
            if config is None:
                config = {}
            
            # 创建蓝图数据
            blueprint_data = self._create_blueprint_data(redstone_notes, config)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(blueprint_data, f, indent=2, ensure_ascii=False)
            
            print(f"[Blueprint] 完成: {output_path} ({os.path.getsize(output_path)} 字节)")
            return True
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"[Blueprint错误] 生成失败: {str(e)}")
            return False
    
    def _create_schematic_data(self, redstone_notes, config):
        """创建Schematic数据"""
        # 计算尺寸
        max_ticks = max([note['time_ticks'] for note in redstone_notes]) if redstone_notes else 0
        width = min(max(max_ticks // 5 + 5, 10), 128)
        height = min(config.get('height', 6), 64)
        length = min(max(len(redstone_notes) // 5 + 5, 8), 128)
        
        block_count = width * height * length
        blocks = bytearray(block_count)
        data = bytearray(block_count)
        
        # 放置基础层
        self._create_base_layer(blocks, data, width, height, length, config)
        
        # 放置音符盒和电路
        self._place_redstone_circuit(blocks, data, redstone_notes, width, height, length, config)
        
        # 创建Schematic字节数据
        schematic = io.BytesIO()
        
        # 版本号
        version = config.get('schematic_version', 2)
        schematic.write(struct.pack('>h', version))
        
        # 尺寸
        schematic.write(struct.pack('>h', width))
        schematic.write(struct.pack('>h', height))
        schematic.write(struct.pack('>h', length))
        
        # 方块数组
        schematic.write(blocks)
        
        # 方块数据数组
        schematic.write(data)
        
        # 实体列表
        if config.get('include_entities', False):
            schematic.write(struct.pack('>h', 0))  # 暂无实体
        else:
            schematic.write(struct.pack('>h', 0))
        
        # TileEntity列表
        if config.get('include_tile_entities', True):
            tile_entities = self._create_tile_entities(redstone_notes, width, height, length)
            schematic.write(struct.pack('>h', len(tile_entities)))
            for entity in tile_entities:
                entity_data = json.dumps(entity).encode('utf-8')
                schematic.write(struct.pack('>h', len(entity_data)))
                schematic.write(entity_data)
        else:
            schematic.write(struct.pack('>h', 0))
        
        # 扩展数据（版本2）
        if version >= 2:
            schematic.write(struct.pack('>h', 0))
        
        # 材料类型
        schematic.write(struct.pack('>h', 0))
        
        return schematic.getvalue()
    
    def _create_litematic_data(self, redstone_notes, config):
        """创建Litematic数据"""
        # 创建简化的Litematic结构
        litematic_structure = {
            "Minecraft": {
                "Version": 2730,
                "FormatVersion": 6
            },
            "Regions": {
                "generated": self._create_litematic_region(redstone_notes, config)
            },
            "Metadata": self._create_litematic_metadata(redstone_notes, config)
        }
        
        # 转换为NBT格式（简化）
        return json.dumps(litematic_structure).encode('utf-8')
    
    def _create_structure_nbt(self, redstone_notes, config):
        """创建结构方块NBT数据"""
        # 计算尺寸
        max_ticks = max([note['time_ticks'] for note in redstone_notes]) if redstone_notes else 0
        width = min(max(max_ticks // 5 + 5, 10), 32)  # 结构方块限制32格
        height = min(config.get('height', 6), 32)
        length = min(max(len(redstone_notes) // 5 + 5, 8), 32)
        
        # 创建NBT结构
        structure = Compound({
            "DataVersion": Int(2975),  # 1.18.2
            "author": String(config.get('author', 'RedstoneMusicGenerator')),
            "size": List[Int]([Int(width), Int(height), Int(length)]),
            "palette": self._create_structure_palette(),
            "blocks": self._create_structure_blocks(redstone_notes, width, height, length, config),
            "entities": List[Compound]([])
        })
        
        return structure
    
    def _create_blueprint_data(self, redstone_notes, config):
        """创建蓝图数据"""
        # 计算尺寸
        max_ticks = max([note['time_ticks'] for note in redstone_notes]) if redstone_notes else 0
        width = min(max(max_ticks // 5 + 5, 10), 256)
        height = min(config.get('height', 6), 256)
        length = min(max(len(redstone_notes) // 5 + 5, 8), 256)
        
        blueprint = {
            "version": "1.0.0",
            "name": config.get('name', 'Redstone Music'),
            "author": config.get('author', 'RedstoneMusicGenerator'),
            "description": config.get('description', 'Generated redstone music from audio'),
            "size": [width, height, length],
            "created": int(os.path.getmtime(__file__)),
            "blocks": self._create_blueprint_blocks(redstone_notes, width, height, length, config),
            "metadata": {
                "format": "redstone-music",
                "note_count": len(redstone_notes),
                "duration": max_ticks / 10.0,
                "generator_version": "2.3.0"
            }
        }
        
        return blueprint
    
    def _create_base_layer(self, blocks, data, width, height, length, config):
        """创建基础层"""
        base_block = config.get('base_block', 'stone')
        base_id = self.block_ids.get(base_block, 1)
        
        for x in range(width):
            for z in range(length):
                idx = self._get_index(x, 0, z, width, height, length)
                if idx < len(blocks):
                    blocks[idx] = base_id
        
        # 添加装饰层
        if config.get('decorate', True):
            for x in range(width):
                for z in range(length):
                    if x % 5 == 0 or z % 5 == 0:
                        idx = self._get_index(x, 1, z, width, height, length)
                        if idx < len(blocks):
                            blocks[idx] = self.block_ids.get('quartz_block', 155)
    
    def _place_redstone_circuit(self, blocks, data, redstone_notes, width, height, length, config):
        """放置红石电路"""
        placed_notes = 0
        
        for note in redstone_notes:
            time_ticks = note['time_ticks']
            pitch = note['pitch'] % 25
            
            # 计算位置
            x = min(int(time_ticks / 5), width - 2)
            y = 2  # 固定在第二层
            z = placed_notes % (length - 2) + 1
            
            idx = self._get_index(x, y, z, width, height, length)
            
            if idx < len(blocks):
                # 放置音符盒
                blocks[idx] = self.block_ids['note_block']
                data[idx] = pitch
                placed_notes += 1
                
                # 下方放红石粉
                below_idx = self._get_index(x, y-1, z, width, height, length)
                if below_idx < len(blocks):
                    blocks[below_idx] = self.block_ids['redstone_wire']
                    data[below_idx] = 0
                
                # 中继器
                if placed_notes % 5 == 0 and x > 1:
                    repeater_idx = self._get_index(x-1, y-1, z, width, height, length)
                    if repeater_idx < len(blocks):
                        blocks[repeater_idx] = self.block_ids['repeater']
                        data[repeater_idx] = 0
                
                # 红石块电源
                if placed_notes % 10 == 0 and x > 2:
                    block_idx = self._get_index(x-2, y-1, z, width, height, length)
                    if block_idx < len(blocks):
                        blocks[block_idx] = self.block_ids['redstone_block']
        
        # 添加红石时钟
        if placed_notes < 10:
            self._create_redstone_clock(blocks, data, width, height, length)
    
    def _create_tile_entities(self, redstone_notes, width, height, length):
        """创建TileEntity数据（用于音符盒等）"""
        entities = []
        
        for i, note in enumerate(redstone_notes[:50]):  # 限制数量
            x = min(int(note['time_ticks'] / 5), width - 2)
            y = 2
            z = i % (length - 2) + 1
            
            # 音符盒TileEntity
            note_entity = {
                "id": "minecraft:noteblock",
                "x": x,
                "y": y,
                "z": z,
                "note": note['pitch'],
                "instrument": note.get('instrument', 'harp')
            }
            entities.append(note_entity)
        
        return entities
    
    def _create_litematic_region(self, redstone_notes, config):
        """创建Litematic区域数据"""
        # 简化实现
        return {
            "Position": {"x": 0, "y": 0, "z": 0},
            "Size": {"x": 10, "y": 5, "z": 10},
            "BlockStatePalette": ["minecraft:air", "minecraft:stone", "minecraft:note_block"],
            "BlockStates": [0] * 500
        }
    
    def _create_litematic_metadata(self, redstone_notes, config):
        """创建Litematic元数据"""
        return {
            "Name": config.get('name', 'Redstone Music'),
            "Author": config.get('author', 'RedstoneMusicGenerator'),
            "Description": config.get('description', 'Generated from audio'),
            "RegionCount": 1,
            "TimeCreated": int(os.path.getmtime(__file__)),
            "TimeModified": int(os.path.getmtime(__file__)),
            "TotalBlocks": 100,
            "TotalVolume": 500
        }
    
    def _create_structure_palette(self):
        """创建结构方块调色板"""
        palette = [
            Compound({
                "Name": String("minecraft:air"),
                "Properties": Compound({})
            }),
            Compound({
                "Name": String("minecraft:stone"),
                "Properties": Compound({})
            }),
            Compound({
                "Name": String("minecraft:note_block"),
                "Properties": Compound({
                    "instrument": String("harp"),
                    "note": String("0"),
                    "powered": String("false")
                })
            })
        ]
        return List[Compound](palette)
    
    def _create_structure_blocks(self, redstone_notes, width, height, length, config):
        """创建结构方块列表"""
        blocks = []
        
        for i, note in enumerate(redstone_notes[:30]):  # 结构方块限制
            x = min(int(note['time_ticks'] / 5), width - 2)
            y = 2
            z = i % (length - 2) + 1
            
            block = Compound({
                "pos": List[Int]([Int(x), Int(y), Int(z)]),
                "state": Int(2),  # 音符盒在调色板中的索引
                "nbt": Compound({
                    "note": Byte(note['pitch']),
                    "instrument": String(note.get('instrument', 'harp'))
                })
            })
            blocks.append(block)
        
        return List[Compound](blocks)
    
    def _create_blueprint_blocks(self, redstone_notes, width, height, length, config):
        """创建蓝图方块列表"""
        blocks = []
        
        for i, note in enumerate(redstone_notes[:100]):  # 限制数量
            x = min(int(note['time_ticks'] / 5), width - 2)
            y = 2
            z = i % (length - 2) + 1
            
            block = {
                "x": x,
                "y": y,
                "z": z,
                "type": "note_block",
                "data": {
                    "note": note['pitch'],
                    "instrument": note.get('instrument', 'harp'),
                    "powered": False
                }
            }
            blocks.append(block)
        
        return blocks
    
    def _create_redstone_clock(self, blocks, data, width, height, length):
        """创建红石时钟"""
        clock_x, clock_y, clock_z = 2, 1, 2
        
        # 红石火把
        idx = self._get_index(clock_x, clock_y, clock_z, width, height, length)
        if idx < len(blocks):
            blocks[idx] = self.block_ids['redstone_torch']
            data[idx] = 5
        
        # 红石粉
        for x_offset in [1, 2, 3]:
            idx = self._get_index(clock_x + x_offset, clock_y, clock_z, width, height, length)
            if idx < len(blocks):
                blocks[idx] = self.block_ids['redstone_wire']
                data[idx] = 15
        
        # 中继器
        idx = self._get_index(clock_x + 4, clock_y, clock_z, width, height, length)
        if idx < len(blocks):
            blocks[idx] = self.block_ids['repeater']
            data[idx] = 1
        
        # 红石块
        idx = self._get_index(clock_x + 5, clock_y, clock_z, width, height, length)
        if idx < len(blocks):
            blocks[idx] = self.block_ids['redstone_block']
    
    def _get_index(self, x, y, z, width, height, length):
        """计算方块索引"""
        return (y * length + z) * width + x
    
    def _create_default_stats(self, name, width, height, length):
        """创建默认统计信息"""
        return {
            'name': name,
            'dimensions': {'width': width, 'height': height, 'length': length},
            'note_blocks': 10,
            'redstone_dust': 10,
            'repeaters': 2,
            'redstone_length': 50,
            'duration': 5.0,
            'file_size': 5,
            'format': 'unknown'
        }
    
    # 保持原有方法兼容性
    def generate_litematic(self, redstone_notes, output_path, name="RedstoneMusic"):
        """保持原有接口兼容"""
        return self.generate_projection(
            redstone_notes,
            output_path,
            format_type='litematic',
            config={'name': name}
        )
    
    def generate_schematic(self, redstone_notes, output_path):
        """保持原有接口兼容"""
        return self.generate_projection(
            redstone_notes,
            output_path,
            format_type='schematic',
            config={}
        )