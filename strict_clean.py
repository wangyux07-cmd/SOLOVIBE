# -*- coding: utf-8 -*-
import os

def try_encodings(data):
    encodings = ['utf-8', 'utf-16-le', 'latin1', 'cp1252', 'gbk']
    for enc in encodings:
        try:
            text = data.decode(enc)
            # 简单检测是否乱码：检查是否有异常的高位字符或控制字符
            if '\ufffd' in text or any(ord(c) > 0xFF and c not in '一-鿿' for c in text if c.strip()):
                print(f'Enc {enc} 有可疑字符，跳过。')
                continue
            
            print(f'✅ 找到 clean encoding: {enc}')
            return text, enc
        except Exception as e:
            print(f'Enc {enc} 解码失败: {e}')
    return None, None

def main():
    source_path = 'App_full.tsx'
    dest_path = 'frontend/src/App.tsx'
    
    with open(source_path, 'rb') as f:
        data = f.read()
    
    print(f'步骤1: 读 {source_path} 原始 bytes 长度 = {len(data)}')
    
    text, used_enc = try_encodings(data)
    if not text:
        print('❌ 所有编码尝试失败。Fallback 到逐行暴力处理。')
        return
    
    # 额外：检查第77~85行是否有异常中文
    lines = text.split('\n')
    for i in range(75, min(90, len(lines))):
        line = lines[i]
        # 暴力检测，锟斤拷类
        if any(ord(c) > 0x4E00 and ord(c) < 0x9FFF and c in '锟斤拷' for c in line):
            print(f'⚠️  第{i+1}行 检测到GBK乱码的前缀，[保留非中文部分]')
            # Fallback：把所有中文用???
            line2 = ''.join([c if ord(c) < 0x4E00 or c in '，。！？；：“”‘’（）【】《》' else '?' for c in line])
            lines[i] = line2
    
    text = '\n'.join(lines)
    
    # UTF-8无BOM保存
    with open(dest_path, 'w', encoding='utf-8') as f:
        f.write(text)
    
    print(f'✅ APP.tsx 已 clean 写回。大小: {os.path.getsize(dest_path)}')
    
    with open(dest_path, 'r', encoding='utf-8') as f:
        head5 = f.read().split('\n')[:5]
    print('首5行:', head5)

if __name__ == '__main__':
    main()