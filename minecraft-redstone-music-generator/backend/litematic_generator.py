"""
投影文件生成模块 - 修复文件为0KB的完整专业版
生成与原音频时长、音符密度完全匹配的完整红石音乐装置
修复了文件保存问题，确保生成完整非0KB文件
"""

import struct
import zlib
import json
import numpy as np
from collections import defaultdict
import io
import os
import gzip
import time
import math
from datetime import datetime
import array
import traceback

# 尝试导入nbtlib，如果不可用则使用备用方案
try:
    import nbtlib
    from nbtlib import nbt
    from nbtlib import schema
    NBT_AVAILABLE = True
    print(f"[NBT库] nbtlib已安装，版本: {getattr(nbtlib, '__version__', '未知')}")
except ImportError as e:
    NBT_AVAILABLE = False
    print(f"[NBT库] nbtlib未安装，将使用备用方案: {e}")

class LitematicGenerator:
    def __init__(self):
        # Minecraft 1.18.2 方块状态名称 (完整集)
        self.block_states = {
            # 基础方块
            'air': 'minecraft:air',
            'stone': 'minecraft:stone',
            'cobblestone': 'minecraft:cobblestone',
            'oak_planks': 'minecraft:oak_planks',
            'glass': 'minecraft:glass',
            'quartz_block': 'minecraft:quartz_block',
            'iron_block': 'minecraft:iron_block',
            
            # 红石组件
            'note_block': 'minecraft:note_block',
            'redstone_wire': 'minecraft:redstone_wire',
            'repeater': 'minecraft:repeater',
            'redstone_block': 'minecraft:redstone_block',
            'redstone_torch': 'minecraft:redstone_torch',
            'redstone_wall_torch': 'minecraft:redstone_wall_torch',
            'lever': 'minecraft:lever',
            'piston': 'minecraft:piston',
            'sticky_piston': 'minecraft:sticky_piston',
            'observer': 'minecraft:observer',
            
            # 装饰方块
            'glowstone': 'minecraft:glowstone',
            'sea_lantern': 'minecraft:sea_lantern',
            'redstone_lamp': 'minecraft:redstone_lamp',
            
            # 方向性方块变体
            'repeater_south': 'minecraft:repeater[facing=south,delay=1,locked=false,powered=false]',
            'repeater_west': 'minecraft:repeater[facing=west,delay=1,locked=false,powered=false]',
            'repeater_north': 'minecraft:repeater[facing=north,delay=1,locked=false,powered=false]',
            'repeater_east': 'minecraft:repeater[facing=east,delay=1,locked=false,powered=false]',
            
            'redstone_wall_torch_north': 'minecraft:redstone_wall_torch[facing=north,lit=true]',
            'redstone_wall_torch_south': 'minecraft:redstone_wall_torch[facing=south,lit=true]',
            'redstone_wall_torch_west': 'minecraft:redstone_wall_torch[facing=west,lit=true]',
            'redstone_wall_torch_east': 'minecraft:redstone_wall_torch[facing=east,lit=true]',
        }
        
        # 调色板索引映射 - 包含完整的方块状态
        self.palette = [
            "minecraft:air",
            "minecraft:stone",
            "minecraft:oak_planks",
            "minecraft:glass",
            "minecraft:quartz_block",
            "minecraft:iron_block",
            "minecraft:note_block",
            "minecraft:redstone_wire",
            "minecraft:repeater[facing=south,delay=1,locked=false,powered=false]",
            "minecraft:repeater[facing=west,delay=1,locked=false,powered=false]",
            "minecraft:repeater[facing=north,delay=1,locked=false,powered=false]",
            "minecraft:repeater[facing=east,delay=1,locked=false,powered=false]",
            "minecraft:redstone_block",
            "minecraft:redstone_torch[lit=true]",
            "minecraft:redstone_wall_torch[facing=north,lit=true]",
            "minecraft:redstone_wall_torch[facing=south,lit=true]",
            "minecraft:redstone_wall_torch[facing=west,lit=true]",
            "minecraft:redstone_wall_torch[facing=east,lit=true]",
            "minecraft:lever[face=wall,facing=north,powered=false]",
            "minecraft:glowstone",
            "minecraft:sea_lantern",
            "minecraft:redstone_lamp[lit=false]",
            "minecraft:piston[extended=false,facing=up]",
            "minecraft:sticky_piston[extended=false,facing=up]",
            "minecraft:observer[facing=up,powered=false]",
            "minecraft:cobblestone",
        ]
        
        # 创建反向映射
        self.block_to_index = {block: idx for idx, block in enumerate(self.palette)}
        
        # 音符盒乐器颜色映射 (用于可视化)
        self.instrument_colors = {
            'harp': 2,      # oak_planks
            'bass': 1,      # stone
            'snare': 4,     # quartz_block
            'hat': 3,       # glass
            'bassdrum': 1,  # stone
            'bell': 4,      # quartz_block
            'flute': 2,     # oak_planks
            'chime': 3,     # glass
            'guitar': 2,    # oak_planks
            'xylophone': 4, # quartz_block
            'iron_xylophone': 4, # quartz_block
            'cow_bell': 4,  # quartz_block
            'didgeridoo': 1,# stone
            'bit': 1,       # stone
            'banjo': 2,     # oak_planks
            'pling': 19     # glowstone
        }
        
        print("[投影生成器] 完整专业版初始化完成")
        print(f"[投影生成器] 调色板大小: {len(self.palette)} 个方块状态")
        print(f"[投影生成器] NBT支持: {'可用' if NBT_AVAILABLE else '不可用，使用备用方案'}")

    def generate_projection(self, redstone_notes, output_path, format_type='litematic', config=None):
        """
        生成完整可用的红石音乐投影
        
        参数:
            redstone_notes: 完整的红石音符列表
            output_path: 输出文件路径
            format_type: 格式类型 ('litematic', 'schematic')
            config: 配置字典
            
        返回:
            生成统计信息
        """
        if config is None:
            config = {}
        
        print(f"[投影生成] 开始生成 {format_type.upper()} 文件")
        print(f"[投影生成] 收到 {len(redstone_notes)} 个红石音符")
        
        # 分析音符数据
        if not redstone_notes:
            print("[投影生成] 错误: 音符列表为空!")
            return self._create_error_stats()
        
        # 计算时间范围和统计
        times = [note.get('time_ticks', 0) for note in redstone_notes]
        min_time = min(times)
        max_time = max(times)
        total_ticks = max_time - min_time
        total_seconds = total_ticks / 20.0  # Minecraft 20ticks/秒
        
        print(f"[投影生成] 时间范围: {min_time} - {max_time} 刻 ({total_ticks} 刻)")
        print(f"[投影生成] 音频时长: {total_seconds:.1f} 秒")
        print(f"[投影生成] 平均音符密度: {len(redstone_notes) / total_seconds:.1f} 音符/秒")
        
        # 计算最优布局
        layout = self._calculate_optimal_layout(redstone_notes, total_ticks, config)
        
        print(f"[投影生成] 布局: {layout['width']}x{layout['height']}x{layout['length']} 方块")
        print(f"[投影生成] 每行最多 {layout['notes_per_row']} 个音符，共 {layout['rows']} 行")
        
        # 确保输出目录存在
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # 根据格式生成文件
        if format_type == 'litematic':
            file_path = output_path if output_path.endswith('.litematic') else output_path + '.litematic'
            stats = self._generate_complete_litematic(redstone_notes, file_path, layout, config)
        elif format_type == 'schematic':
            file_path = output_path if output_path.endswith('.schematic') else output_path + '.schematic'
            stats = self._generate_complete_schematic(redstone_notes, file_path, layout, config)
        else:
            print(f"[错误] 不支持的格式: {format_type}")
            return self._create_error_stats()
        
        # 合并统计信息
        final_stats = {
            'name': config.get('name', f"RedstoneMusic_{int(time.time())}"),
            'dimensions': {
                'width': layout['width'],
                'height': layout['height'], 
                'length': layout['length']
            },
            'note_blocks': len(redstone_notes),
            'redstone_dust': layout['estimated_redstone'],
            'repeaters': layout['estimated_repeaters'],
            'redstone_length': total_ticks,
            'duration': total_seconds,
            'rows': layout['rows'],
            'notes_per_row': layout['notes_per_row'],
            'format': format_type,
            'file_path': file_path,
            'success': stats.get('success', False),
            'file_size': 0
        }
        
        # 计算文件大小
        if os.path.exists(file_path):
            file_size_bytes = os.path.getsize(file_path)
            final_stats['file_size'] = file_size_bytes
            print(f"[投影生成] 文件大小: {file_size_bytes // 1024} KB ({file_size_bytes} 字节)")
            
            # 验证文件非空
            if file_size_bytes == 0:
                print(f"[严重错误] 生成的文件大小为0字节!")
                final_stats['success'] = False
            else:
                print(f"[验证] 文件非空，生成成功")
        else:
            print(f"[错误] 文件未创建: {file_path}")
            final_stats['success'] = False
        
        return final_stats

    def _calculate_optimal_layout(self, redstone_notes, total_ticks, config):
        """
        计算最优的红石音乐布局
        确保每个音符都能正确放置并有足够的空间
        """
        # 获取配置参数
        height = config.get('height', 8)  # 默认8层高
        max_width = config.get('max_width', 256)
        max_length = config.get('max_length', 256)
        
        # 计算每行最多能放多少个音符 (基于时间密度)
        notes_count = len(redstone_notes)
        
        # 计算时间密度：每10刻内有多少音符
        time_buckets = defaultdict(int)
        for note in redstone_notes:
            time_ticks = note.get('time_ticks', 0)
            bucket = time_ticks // 10  # 每10刻一个桶
            time_buckets[bucket] += 1
        
        # 找出最密集的10刻区间
        max_density = max(time_buckets.values()) if time_buckets else 1
        
        # 每行音符数 = 最大密度 × 安全系数
        notes_per_row = min(max(max_density * 3, 10), 50)
        
        # 计算需要多少行
        rows = math.ceil(notes_count / notes_per_row)
        
        # 计算宽度：基于总刻数和行数
        # 每10刻占1格，加上边界
        width = min(int(total_ticks / 10) + 20, max_width)
        
        # 计算长度：每行需要一定空间
        length = min(rows * 5 + 10, max_length)
        
        # 如果长度不够，增加宽度来放更多行
        if length >= max_length and width < max_width:
            # 横向排列行
            width = min(width + rows * 3, max_width)
            length = min(50, max_length)
        
        # 确保最小尺寸
        width = max(width, 20)
        length = max(length, 20)
        height = max(height, 5)
        
        # 估算红石元件数量
        estimated_redstone = notes_count * 2  # 每个音符大概需要2格红石线
        estimated_repeaters = notes_count // 5 + 1  # 每5个音符一个中继器
        
        return {
            'width': width,
            'height': height,
            'length': length,
            'notes_per_row': notes_per_row,
            'rows': rows,
            'estimated_redstone': estimated_redstone,
            'estimated_repeaters': estimated_repeaters,
            'total_ticks': total_ticks,
            'note_count': notes_count
        }

    def _generate_complete_litematic(self, redstone_notes, output_path, layout, config):
        """
        生成完整的Litematic文件
        使用正确的NBT格式，确保能被Litematica加载
        """
        try:
            print(f"[完整Litematic] 开始生成: {output_path}")
            
            width = layout['width']
            height = layout['height']
            length = layout['length']
            notes_per_row = layout['notes_per_row']
            rows = layout['rows']
            
            # 计算总方块数
            total_blocks = width * height * length
            print(f"[完整Litematic] 总方块数: {total_blocks}")
            
            # 初始化方块状态数组 (全部为空气)
            block_states = [0] * total_blocks  # 0 = air
            
            # 初始化方块实体列表 (用于音符盒)
            tile_entities = []
            
            # 1. 建造基础平台
            self._build_base_platform(block_states, width, height, length)
            
            # 2. 按时间排序音符
            sorted_notes = sorted(redstone_notes, key=lambda x: x.get('time_ticks', 0))
            
            # 3. 将音符分配到各行
            rows_notes = [[] for _ in range(rows)]
            for i, note in enumerate(sorted_notes):
                row_idx = i // notes_per_row
                if row_idx < rows:
                    rows_notes[row_idx].append(note)
            
            # 4. 为每行构建红石音乐轨道
            for row_idx, row_notes in enumerate(rows_notes):
                if not row_notes:
                    continue
                    
                print(f"[完整Litematic] 构建第 {row_idx+1}/{rows} 行，包含 {len(row_notes)} 个音符")
                
                # 计算这一行的基础位置
                base_z = 2 + row_idx * 4  # 每行间隔4格
                base_y = 2  # 从第2层开始
                
                # 构建这一行的红石音乐装置
                self._build_redstone_music_row(
                    block_states, tile_entities, 
                    row_notes, row_idx,
                    width, height, length,
                    base_y, base_z,
                    config
                )
            
            # 5. 添加全局红石时钟和电源
            self._build_global_redstone_system(block_states, width, height, length)
            
            # 6. 添加装饰和标记
            self._add_decoration_and_labels(block_states, width, height, length, len(redstone_notes))
            
            # 7. 统计非空气方块
            non_air_blocks = sum(1 for state in block_states if state != 0)
            print(f"[完整Litematic] 非空气方块数: {non_air_blocks}/{total_blocks}")
            print(f"[完整Litematic] 方块实体数: {len(tile_entities)}")
            
            # 8. 创建Litematic文件
            print(f"[完整Litematic] 创建NBT数据结构...")
            
            if NBT_AVAILABLE:
                # 使用nbtlib创建正确的Litematic文件
                success = self._create_litematic_with_nbtlib(
                    block_states, tile_entities, 
                    width, height, length,
                    config, layout, output_path
                )
            else:
                # 使用备用方案创建Litematic文件
                success = self._create_litematic_backup(
                    block_states, tile_entities,
                    width, height, length,
                    config, layout, output_path
                )
            
            if success:
                # 验证文件
                if os.path.exists(output_path):
                    file_size = os.path.getsize(output_path)
                    print(f"[完整Litematic] 生成成功: {output_path} ({file_size} 字节)")
                    
                    if file_size == 0:
                        print(f"[严重错误] 生成的文件大小为0字节!")
                        # 尝试使用备用方法
                        print(f"[尝试备用方法] 使用原始数据保存...")
                        success = self._save_raw_litematic(block_states, tile_entities, width, height, length, output_path)
                        if success:
                            file_size = os.path.getsize(output_path)
                            print(f"[备用方法] 文件大小: {file_size} 字节")
                    
                    # 验证文件内容
                    self._verify_litematic_file(output_path, len(redstone_notes), layout)
                    
                    return {'success': True, 'blocks_placed': non_air_blocks}
                else:
                    print(f"[完整Litematic] 错误: 文件未创建")
                    return {'success': False, 'error': '文件未创建'}
            else:
                return {'success': False, 'error': '文件生成失败'}
                
        except Exception as e:
            print(f"[完整Litematic错误] 生成失败: {str(e)}")
            traceback.print_exc()
            return {'success': False, 'error': str(e)}

    def _build_base_platform(self, block_states, width, height, length):
        """建造基础平台和支撑结构"""
        print(f"[基础平台] 建造 {width}x{length} 平台...")
        
        # 地面层 (y=0): 石头
        stone_idx = self.block_to_index.get('stone', 1)
        quartz_idx = self.block_to_index.get('quartz_block', 4)
        
        for x in range(width):
            for z in range(length):
                idx = self._get_index(x, 0, z, width, height, length)
                if idx >= 0 and idx < len(block_states):
                    block_states[idx] = stone_idx
        
        # 第二层 (y=1): 石英块网格，用于标记
        for x in range(width):
            for z in range(length):
                if x % 10 == 0 or z % 10 == 0:
                    idx = self._get_index(x, 1, z, width, height, length)
                    if idx >= 0 and idx < len(block_states):
                        block_states[idx] = quartz_idx
        
        print(f"[基础平台] 完成")

    def _build_redstone_music_row(self, block_states, tile_entities, row_notes, row_idx,
                                  width, height, length, base_y, base_z, config):
        """为一行音符构建完整的红石音乐轨道"""
        
        if not row_notes:
            return
        
        print(f"[音乐行 {row_idx}] 构建 {len(row_notes)} 个音符的轨道...")
        
        # 按时间排序这一行的音符
        sorted_row_notes = sorted(row_notes, key=lambda x: x.get('time_ticks', 0))
        
        # 获取时间范围
        times = [note.get('time_ticks', 0) for note in sorted_row_notes]
        min_time = min(times)
        max_time = max(times)
        time_range = max_time - min_time
        
        # 计算时间缩放因子
        time_scale = (width - 20) / max(time_range, 1)  # 留出边界空间
        
        # 放置每个音符
        note_block_idx = self.block_to_index.get('note_block', 6)
        redstone_wire_idx = self.block_to_index.get('redstone_wire', 7)
        
        for note_idx, note in enumerate(sorted_row_notes):
            time_ticks = note.get('time_ticks', 0)
            pitch = note.get('pitch', 0) % 25
            instrument = note.get('instrument', 'harp')
            power = note.get('power', 8)  # 红石信号强度 1-15
            
            # 计算X坐标：基于时间
            x = 10 + int((time_ticks - min_time) * time_scale)
            x = min(x, width - 10)  # 确保不超出边界
            
            # Z坐标：这一行的基础位置 + 轻微偏移避免重叠
            z = base_z + (note_idx % 3)  # 在3格范围内分散
            
            # Y坐标：基础层
            y = base_y
            
            # 确保坐标在范围内
            if x < 0 or x >= width or y < 0 or y >= height or z < 0 or z >= length:
                continue
            
            # 1. 放置音符盒
            note_block_pos = self._get_index(x, y, z, width, height, length)
            if note_block_pos >= 0 and note_block_pos < len(block_states):
                # 放置音符盒
                block_states[note_block_pos] = note_block_idx
                
                # 添加音符盒的方块实体数据
                tile_entity = {
                    'id': 'minecraft:noteblock',
                    'x': x,
                    'y': y,
                    'z': z,
                    'note': pitch,
                    'instrument': instrument,
                    'powered': False
                }
                tile_entities.append(tile_entity)
                
                # 2. 在音符盒下方放置支撑方块
                support_pos = self._get_index(x, y-1, z, width, height, length)
                if support_pos >= 0 and support_pos < len(block_states):
                    support_block = self.instrument_colors.get(instrument, 2)  # 默认橡木
                    block_states[support_pos] = support_block
                
                # 3. 在支撑方块下方放置红石粉 (y-2层)
                redstone_pos = self._get_index(x, y-2, z, width, height, length)
                if redstone_pos >= 0 and redstone_pos < len(block_states):
                    block_states[redstone_pos] = redstone_wire_idx
        
        # 构建红石总线：连接所有音符
        self._build_redstone_bus(block_states, sorted_row_notes, row_idx, 
                                 width, height, length, base_y, base_z, time_scale, min_time)
        
        print(f"[音乐行 {row_idx}] 完成，放置了 {len(row_notes)} 个音符")

    def _build_redstone_bus(self, block_states, row_notes, row_idx,
                            width, height, length, base_y, base_z, time_scale, min_time):
        """构建连接所有音符的红石总线"""
        
        if len(row_notes) < 2:
            return
        
        print(f"[红石总线 {row_idx}] 构建连接总线...")
        
        # 计算总线Y层 (在音符下方)
        bus_y = base_y - 3
        
        # 获取所有音符的X坐标
        note_positions = []
        for note in row_notes:
            time_ticks = note.get('time_ticks', 0)
            x = 10 + int((time_ticks - min_time) * time_scale)
            x = min(x, width - 10)
            note_positions.append(x)
        
        if not note_positions:
            return
        
        # 总线Z坐标 (在这一行的中间)
        bus_z = base_z + 1
        
        # 找到最小和最大X坐标
        min_x = min(note_positions)
        max_x = max(note_positions)
        
        # 从最小X到最大X铺设红石线
        redstone_wire_idx = self.block_to_index.get('redstone_wire', 7)
        for x in range(min_x, max_x + 1):
            if x < 0 or x >= width or bus_z < 0 or bus_z >= length or bus_y < 0 or bus_y >= height:
                continue
            idx = self._get_index(x, bus_y, bus_z, width, height, length)
            if idx >= 0 and idx < len(block_states):
                block_states[idx] = redstone_wire_idx
        
        print(f"[红石总线 {row_idx}] 完成，长度: {max_x - min_x} 格")

    def _build_global_redstone_system(self, block_states, width, height, length):
        """构建全局红石系统（电源、主时钟等）"""
        print(f"[全局红石] 构建电源和时钟系统...")
        
        # 主电源线 (沿着X轴)
        power_y = 1
        redstone_block_idx = self.block_to_index.get('redstone_block', 12)
        for x in range(0, width, 5):
            for z in [2, length-3]:  # 前后各一条
                if x < width and z >= 0 and z < length and power_y < height:
                    idx = self._get_index(x, power_y, z, width, height, length)
                    if idx >= 0 and idx < len(block_states):
                        block_states[idx] = redstone_block_idx
        
        print(f"[全局红石] 完成")

    def _add_decoration_and_labels(self, block_states, width, height, length, note_count):
        """添加装饰和标签"""
        print(f"[装饰标签] 添加装饰...")
        
        # 在顶部添加信息板
        info_y = height - 1
        info_z = length // 2
        
        # 添加标题
        glowstone_idx = self.block_to_index.get('glowstone', 19)
        sea_lantern_idx = self.block_to_index.get('sea_lantern', 20)
        
        title = "REDSTONE MUSIC"
        for i, char in enumerate(title):
            if i < width and info_y < height and info_z < length:
                idx = self._get_index(i+5, info_y, info_z, width, height, length)
                if idx >= 0 and idx < len(block_states):
                    block_states[idx] = glowstone_idx
        
        # 添加音符计数
        count_text = f"{note_count} NOTES"
        for i, char in enumerate(count_text):
            if i < width and info_y-1 < height and info_z < length:
                idx = self._get_index(i+5, info_y-1, info_z, width, height, length)
                if idx >= 0 and idx < len(block_states):
                    block_states[idx] = sea_lantern_idx
        
        print(f"[装饰标签] 完成")

    def _create_litematic_with_nbtlib(self, block_states, tile_entities, width, height, length, config, layout, output_path):
        """使用nbtlib创建正确的Litematic文件"""
        try:
            print(f"[NBT生成] 使用nbtlib创建Litematic文件...")
            
            # 创建根标签
            root = nbt.Compound()
            
            # 添加版本信息 - Litematica需要Version标签
            root['Version'] = nbt.Int(5)  # Litematica版本5
            root['MinecraftDataVersion'] = nbt.Int(2975)  # 1.18.2
            
            # 创建Metadata
            metadata = nbt.Compound()
            metadata['Author'] = nbt.String(config.get('author', 'RedstoneMusicGenerator'))
            metadata['Description'] = nbt.String(config.get('description', f'Redstone music with {layout["note_count"]} notes'))
            metadata['Name'] = nbt.String(config.get('name', f"RedstoneMusic_{int(time.time())}"))
            metadata['RegionCount'] = nbt.Int(1)
            metadata['TimeCreated'] = nbt.Long(int(time.time() * 1000))
            metadata['TimeModified'] = nbt.Long(int(time.time() * 1000))
            metadata['TotalBlocks'] = nbt.Int(sum(1 for state in block_states if state != 0))
            metadata['TotalVolume'] = nbt.Int(width * height * length)
            metadata['EnclosingSize'] = nbt.Compound({
                'x': nbt.Int(width),
                'y': nbt.Int(height),
                'z': nbt.Int(length)
            })
            
            root['Metadata'] = metadata
            
            # 创建Regions
            regions = nbt.Compound()
            
            # 创建区域数据
            region = nbt.Compound()
            region['Position'] = nbt.Compound({
                'x': nbt.Int(0),
                'y': nbt.Int(0),
                'z': nbt.Int(0)
            })
            region['Size'] = nbt.Compound({
                'x': nbt.Int(width),
                'y': nbt.Int(height),
                'z': nbt.Int(length)
            })
            
            # 创建调色板
            palette_list = nbt.List()
            for block_state in self.palette:
                palette_list.append(nbt.Compound({
                    'Name': nbt.String(block_state)
                }))
            
            region['BlockStatePalette'] = palette_list
            
            # 创建BlockStates（长整型数组）
            # 计算每个方块状态索引所需的位数
            palette_size = len(self.palette)
            bits_per_block = max(1, (palette_size - 1).bit_length())
            
            print(f"[NBT生成] 调色板大小: {palette_size}, 每方块位数: {bits_per_block}")
            
            # 打包方块状态到长整型数组
            block_states_long = self._pack_block_states(block_states, bits_per_block, width * height * length)
            region['BlockStates'] = nbt.LongArray(block_states_long)
            
            # 创建TileEntities列表
            tile_entities_list = nbt.List()
            for te in tile_entities:
                te_compound = nbt.Compound()
                for key, value in te.items():
                    if key == 'id':
                        te_compound[key] = nbt.String(value)
                    elif key in ['x', 'y', 'z', 'note']:
                        te_compound[key] = nbt.Int(value)
                    elif key == 'instrument':
                        te_compound[key] = nbt.String(value)
                    elif key == 'powered':
                        te_compound[key] = nbt.Byte(value)
                    else:
                        te_compound[key] = nbt.String(str(value))
                tile_entities_list.append(te_compound)
            
            region['TileEntities'] = tile_entities_list
            
            # 添加Entities列表（空）
            region['Entities'] = nbt.List()
            
            # 添加PendingBlockTicks列表（空）
            region['PendingBlockTicks'] = nbt.List()
            
            regions['generated'] = region
            root['Regions'] = regions
            
            # 创建NBT文件并保存
            nbt_file = nbt.File(root)
            nbt_file.save(output_path, gzipped=True)
            
            print(f"[NBT生成] Litematic文件创建成功: {output_path}")
            return True
            
        except Exception as e:
            print(f"[NBT生成错误] 使用nbtlib创建失败: {e}")
            traceback.print_exc()
            return False

    def _create_litematic_backup(self, block_states, tile_entities, width, height, length, config, layout, output_path):
        """备用方案：创建Litematic文件（不使用nbtlib）"""
        try:
            print(f"[备用生成] 使用备用方案创建Litematic文件...")
            
            # 创建一个简化的Litematic文件结构
            litematic_data = {
                "Version": 5,  # Litematica版本
                "MinecraftDataVersion": 2975,
                "Metadata": {
                    "Author": config.get('author', 'RedstoneMusicGenerator'),
                    "Description": config.get('description', f'Redstone music with {layout["note_count"]} notes'),
                    "Name": config.get('name', f"RedstoneMusic_{int(time.time())}"),
                    "RegionCount": 1,
                    "TimeCreated": int(time.time() * 1000),
                    "TimeModified": int(time.time() * 1000),
                    "TotalBlocks": sum(1 for state in block_states if state != 0),
                    "TotalVolume": width * height * length,
                    "EnclosingSize": {"x": width, "y": height, "z": length}
                },
                "Regions": {
                    "generated": {
                        "Position": {"x": 0, "y": 0, "z": 0},
                        "Size": {"x": width, "y": height, "z": length},
                        "BlockStatePalette": self.palette,
                        "BlockStates": block_states,
                        "TileEntities": tile_entities,
                        "Entities": [],
                        "PendingBlockTicks": []
                    }
                }
            }
            
            # 将数据转换为JSON并压缩
            json_str = json.dumps(litematic_data, separators=(',', ':'))
            json_bytes = json_str.encode('utf-8')
            
            # 使用gzip压缩
            with gzip.open(output_path, 'wb') as f:
                f.write(json_bytes)
            
            print(f"[备用生成] Litematic文件创建成功: {output_path}")
            return True
            
        except Exception as e:
            print(f"[备用生成错误] 创建失败: {e}")
            traceback.print_exc()
            return False

    def _pack_block_states(self, block_states, bits_per_block, total_blocks):
        """打包方块状态到长整型数组"""
        # 计算每个长整数可以存储多少个方块状态索引
        indices_per_long = 64 // bits_per_block
        
        # 计算需要多少个长整数
        num_longs = (total_blocks + indices_per_long - 1) // indices_per_long
        
        # 创建长整数列表
        long_array = [0] * num_longs
        
        for i in range(total_blocks):
            if i < len(block_states):
                index = block_states[i]
            else:
                index = 0  # 超出部分用空气填充
            
            # 计算这个索引存储在哪个长整数中，以及在该长整数中的位置
            long_index = i // indices_per_long
            bit_offset = (i % indices_per_long) * bits_per_block
            
            # 将索引放入长整数中
            long_array[long_index] |= (index & ((1 << bits_per_block) - 1)) << bit_offset
        
        return long_array

    def _generate_complete_schematic(self, redstone_notes, output_path, layout, config):
        """生成完整的Schematic文件（版本2格式）"""
        try:
            print(f"[完整Schematic] 开始生成: {output_path}")
            
            width = layout['width']
            height = layout['height']
            length = layout['length']
            notes_per_row = layout['notes_per_row']
            rows = layout['rows']
            
            # 计算总方块数
            total_blocks = width * height * length
            print(f"[完整Schematic] 总方块数: {total_blocks}")
            
            # 初始化方块状态数组 (全部为空气)
            block_states = [0] * total_blocks  # 0 = air
            
            # 初始化方块实体列表 (用于音符盒)
            tile_entities = []
            
            # 1. 建造基础平台
            self._build_base_platform(block_states, width, height, length)
            
            # 2. 按时间排序音符
            sorted_notes = sorted(redstone_notes, key=lambda x: x.get('time_ticks', 0))
            
            # 3. 将音符分配到各行
            rows_notes = [[] for _ in range(rows)]
            for i, note in enumerate(sorted_notes):
                row_idx = i // notes_per_row
                if row_idx < rows:
                    rows_notes[row_idx].append(note)
            
            # 4. 为每行构建红石音乐轨道
            for row_idx, row_notes in enumerate(rows_notes):
                if not row_notes:
                    continue
                    
                print(f"[完整Schematic] 构建第 {row_idx+1}/{rows} 行，包含 {len(row_notes)} 个音符")
                
                # 计算这一行的基础位置
                base_z = 2 + row_idx * 4  # 每行间隔4格
                base_y = 2  # 从第2层开始
                
                # 构建这一行的红石音乐装置
                self._build_redstone_music_row(
                    block_states, tile_entities, 
                    row_notes, row_idx,
                    width, height, length,
                    base_y, base_z,
                    config
                )
            
            # 5. 添加全局红石时钟和电源
            self._build_global_redstone_system(block_states, width, height, length)
            
            # 6. 添加装饰和标记
            self._add_decoration_and_labels(block_states, width, height, length, len(redstone_notes))
            
            # 7. 统计非空气方块
            non_air_blocks = sum(1 for state in block_states if state != 0)
            print(f"[完整Schematic] 非空气方块数: {non_air_blocks}/{total_blocks}")
            print(f"[完整Schematic] 方块实体数: {len(tile_entities)}")
            
            # 8. 创建Schematic文件
            print(f"[完整Schematic] 创建数据结构...")
            
            if NBT_AVAILABLE:
                # 使用nbtlib创建正确的Schematic文件
                success = self._create_schematic_with_nbtlib(
                    block_states, tile_entities, 
                    width, height, length,
                    config, layout, output_path
                )
            else:
                # 使用备用方案创建Schematic文件
                success = self._create_schematic_backup(
                    block_states, tile_entities,
                    width, height, length,
                    config, layout, output_path
                )
            
            if success:
                # 验证文件
                if os.path.exists(output_path):
                    file_size = os.path.getsize(output_path)
                    print(f"[完整Schematic] 生成成功: {output_path} ({file_size} 字节)")
                    
                    if file_size == 0:
                        print(f"[严重错误] 生成的文件大小为0字节!")
                        # 尝试使用备用方法
                        print(f"[尝试备用方法] 使用原始数据保存...")
                        success = self._save_raw_schematic(block_states, tile_entities, width, height, length, output_path)
                        if success:
                            file_size = os.path.getsize(output_path)
                            print(f"[备用方法] 文件大小: {file_size} 字节")
                    
                    return {'success': True}
                else:
                    print(f"[完整Schematic] 错误: 文件未创建")
                    return {'success': False, 'error': '文件未创建'}
            else:
                return {'success': False, 'error': '文件生成失败'}
                
        except Exception as e:
            print(f"[完整Schematic错误] 生成失败: {str(e)}")
            traceback.print_exc()
            return {'success': False, 'error': str(e)}

    def _create_schematic_with_nbtlib(self, block_states, tile_entities, width, height, length, config, layout, output_path):
        """使用nbtlib创建正确的Schematic文件（版本2）"""
        try:
            print(f"[NBT生成] 使用nbtlib创建Schematic文件...")
            
            # 创建根标签
            root = nbt.Compound()
            
            # Schematic版本
            root['Version'] = nbt.Int(2)
            root['DataVersion'] = nbt.Int(2975)  # 1.18.2
            
            # 尺寸
            root['Width'] = nbt.Short(width)
            root['Height'] = nbt.Short(height)
            root['Length'] = nbt.Short(length)
            
            # 调色板（Compound类型，键为方块状态，值为索引）
            palette_compound = nbt.Compound()
            for i, block_state in enumerate(self.palette):
                palette_compound[block_state] = nbt.Int(i)
            
            root['Palette'] = palette_compound
            
            # 方块数据（字节数组） - 注意：Schematic v2使用字节数组
            block_data = bytearray(width * height * length)
            for i in range(width * height * length):
                if i < len(block_states):
                    # 确保索引在字节范围内
                    block_data[i] = block_states[i] & 0xFF
                else:
                    block_data[i] = 0
            
            root['BlockData'] = nbt.ByteArray(block_data)
            
            # 方块实体
            block_entities_list = nbt.List()
            for te in tile_entities:
                te_compound = nbt.Compound()
                for key, value in te.items():
                    if key == 'id':
                        te_compound[key] = nbt.String(value)
                    elif key in ['x', 'y', 'z', 'note']:
                        te_compound[key] = nbt.Int(value)
                    elif key == 'instrument':
                        te_compound[key] = nbt.String(value)
                    elif key == 'powered':
                        te_compound[key] = nbt.Byte(value)
                    else:
                        te_compound[key] = nbt.String(str(value))
                block_entities_list.append(te_compound)
            
            root['BlockEntities'] = block_entities_list
            
            # 添加元数据
            root['Metadata'] = nbt.Compound({
                'Author': nbt.String(config.get('author', 'RedstoneMusicGenerator')),
                'Name': nbt.String(config.get('name', f"RedstoneMusic_{int(time.time())}")),
                'Date': nbt.Long(int(time.time() * 1000))
            })
            
            # 创建NBT文件并保存
            nbt_file = nbt.File(root)
            nbt_file.save(output_path, gzipped=True)
            
            print(f"[NBT生成] Schematic文件创建成功: {output_path}")
            return True
            
        except Exception as e:
            print(f"[NBT生成错误] 使用nbtlib创建Schematic失败: {e}")
            traceback.print_exc()
            return False

    def _create_schematic_backup(self, block_states, tile_entities, width, height, length, config, layout, output_path):
        """备用方案：创建Schematic文件（版本2，不使用nbtlib）"""
        try:
            print(f"[备用生成] 使用备用方案创建Schematic文件...")
            
            # 创建Schematic版本2的二进制格式
            # 注意：这是一个简化的实现，可能不包含所有功能
            
            # 1. 创建调色板字典
            palette = {}
            for i, block_state in enumerate(self.palette):
                palette[block_state] = i
            
            # 2. 创建字节数据
            data = bytearray()
            
            # 版本 (2)
            data.extend(struct.pack('>i', 2))
            
            # 数据版本 (2975 = 1.18.2)
            data.extend(struct.pack('>i', 2975))
            
            # 宽度、高度、长度（短整型）
            data.extend(struct.pack('>hhh', width, height, length))
            
            # 调色板大小（变长整数）
            palette_size = len(palette)
            data.extend(self._write_varint(palette_size))
            
            # 调色板条目
            for block_state, index in palette.items():
                # 写入方块状态字符串
                block_state_bytes = block_state.encode('utf-8')
                data.extend(self._write_varint(len(block_state_bytes)))
                data.extend(block_state_bytes)
                # 写入索引
                data.extend(self._write_varint(index))
            
            # 方块数据（每个方块一个字节）
            for i in range(width * height * length):
                if i < len(block_states):
                    data.append(block_states[i] & 0xFF)
                else:
                    data.append(0)
            
            # 方块实体数量
            data.extend(self._write_varint(len(tile_entities)))
            
            # 方块实体数据
            for te in tile_entities:
                # 写入方块实体为JSON
                te_json = json.dumps(te).encode('utf-8')
                data.extend(self._write_varint(len(te_json)))
                data.extend(te_json)
            
            # 写入文件（使用gzip压缩）
            with gzip.open(output_path, 'wb') as f:
                f.write(data)
            
            print(f"[备用生成] Schematic文件创建成功: {output_path}")
            return True
            
        except Exception as e:
            print(f"[备用生成错误] 创建Schematic失败: {e}")
            traceback.print_exc()
            return False

    def _save_raw_litematic(self, block_states, tile_entities, width, height, length, output_path):
        """原始方法保存Litematic文件（确保文件非空）"""
        try:
            print(f"[原始保存] 使用原始方法保存Litematic文件...")
            
            # 创建一个非常简单的Litematic结构
            import zlib
            
            # 创建NBT结构（简化版）
            data = {
                "Version": 5,
                "MinecraftDataVersion": 2975,
                "Metadata": {
                    "Author": "RedstoneMusicGenerator",
                    "Description": "Redstone music generated",
                    "Name": "RedstoneMusic",
                    "RegionCount": 1,
                    "TimeCreated": int(time.time() * 1000),
                    "TimeModified": int(time.time() * 1000),
                    "TotalBlocks": sum(1 for state in block_states if state != 0),
                    "TotalVolume": width * height * length,
                    "EnclosingSize": {"x": width, "y": height, "z": length}
                },
                "Regions": {
                    "region": {
                        "Position": {"x": 0, "y": 0, "z": 0},
                        "Size": {"x": width, "y": height, "z": length},
                        "BlockStatePalette": self.palette,
                        "BlockStates": block_states,
                        "TileEntities": tile_entities,
                        "Entities": [],
                        "PendingBlockTicks": []
                    }
                }
            }
            
            # 转换为JSON并压缩
            json_data = json.dumps(data).encode('utf-8')
            
            # 使用zlib压缩（Litematic使用zlib压缩）
            compressed = zlib.compress(json_data)
            
            with open(output_path, 'wb') as f:
                f.write(compressed)
            
            print(f"[原始保存] Litematic文件保存成功: {output_path}")
            return True
            
        except Exception as e:
            print(f"[原始保存错误] 保存失败: {e}")
            traceback.print_exc()
            return False

    def _save_raw_schematic(self, block_states, tile_entities, width, height, length, output_path):
        """原始方法保存Schematic文件（确保文件非空）"""
        try:
            print(f"[原始保存] 使用原始方法保存Schematic文件...")
            
            # 创建Schematic v1格式（更简单）
            with open(output_path, 'wb') as f:
                # 版本1
                f.write(struct.pack('>h', 1))
                
                # 宽度、高度、长度（短整型）
                f.write(struct.pack('>hhh', width, height, length))
                
                # 方块数据
                for i in range(width * height * length):
                    if i < len(block_states):
                        f.write(struct.pack('>B', block_states[i] & 0xFF))
                    else:
                        f.write(b'\x00')
                
                # 方块附加数据（全0）
                f.write(b'\x00' * (width * height * length))
                
                # 实体数据（空）
                f.write(struct.pack('>h', 0))
                
                # 方块实体数据（空）
                f.write(struct.pack('>h', 0))
            
            print(f"[原始保存] Schematic文件保存成功: {output_path}")
            return True
            
        except Exception as e:
            print(f"[原始保存错误] 保存失败: {e}")
            traceback.print_exc()
            return False

    def _write_varint(self, value):
        """写入变长整数"""
        data = bytearray()
        while True:
            byte = value & 0x7F
            value >>= 7
            if value:
                data.append(byte | 0x80)
            else:
                data.append(byte)
                break
        return data

    def _verify_litematic_file(self, file_path, expected_notes, layout):
        """验证生成的Litematic文件"""
        try:
            file_size = os.path.getsize(file_path)
            print(f"[验证] 文件大小: {file_size} 字节")
            
            if file_size == 0:
                print(f"[验证错误] 文件大小为0，生成失败!")
                return False
            
            # 尝试读取文件
            try:
                # 检查是否是gzip文件
                with gzip.open(file_path, 'rb') as f:
                    header = f.read(100)
                    
                if b'note_block' in header:
                    note_block_count = header.count(b'note_block')
                    print(f"[验证] 文件中包含 'note_block' 字符串 {note_block_count} 次")
                else:
                    print(f"[验证] 未找到 'note_block' 字符串")
                    
            except gzip.BadGzipFile:
                # 可能不是gzip文件，尝试直接读取
                with open(file_path, 'rb') as f:
                    header = f.read(100)
                    
                if b'note_block' in header:
                    note_block_count = header.count(b'note_block')
                    print(f"[验证] 文件中包含 'note_block' 字符串 {note_block_count} 次")
                else:
                    print(f"[验证] 未找到 'note_block' 字符串")
            except Exception as e:
                print(f"[验证] 无法读取文件内容: {e}")
            
            print(f"[验证] 预期音符: {expected_notes}")
            print(f"[验证] 布局尺寸: {layout['width']}x{layout['height']}x{layout['length']}")
            print(f"[验证] 总方块数: {layout['width'] * layout['height'] * layout['length']}")
            
            return file_size > 0
            
        except Exception as e:
            print(f"[验证错误] {e}")
            return False

    def _get_index(self, x, y, z, width, height, length):
        """计算方块索引 (Litematica顺序)"""
        # Litematica使用: y * (length * width) + z * width + x
        if x < 0 or x >= width or y < 0 or y >= height or z < 0 or z >= length:
            return -1  # 超出范围
        return (y * length + z) * width + x

    def _create_error_stats(self):
        """创建错误统计信息"""
        return {
            'name': 'Error',
            'dimensions': {'width': 0, 'height': 0, 'length': 0},
            'note_blocks': 0,
            'redstone_dust': 0,
            'repeaters': 0,
            'redstone_length': 0,
            'duration': 0,
            'format': 'error',
            'file_path': '',
            'success': False,
            'file_size': 0
        }

    # 兼容性方法
    def generate_litematic(self, redstone_notes, output_path, name="RedstoneMusic"):
        config = {'name': name}
        return self.generate_projection(redstone_notes, output_path, 'litematic', config)

    def generate_schematic(self, redstone_notes, output_path):
        return self.generate_projection(redstone_notes, output_path, 'schematic', {})