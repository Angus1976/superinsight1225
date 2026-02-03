#!/bin/bash
# Kiro 信任命令管理脚本

SETTINGS_FILE="$HOME/Library/Application Support/Kiro/User/settings.json"

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 检查 jq 是否安装
if ! command -v jq &> /dev/null; then
    echo -e "${RED}错误: 需要安装 jq 工具${NC}"
    echo "安装方法: brew install jq"
    exit 1
fi

# 显示当前信任列表
show_trusted_commands() {
    echo -e "${GREEN}当前信任的命令前缀:${NC}"
    jq -r '.["kiroAgent.trustedCommands"][]' "$SETTINGS_FILE" 2>/dev/null | nl
}

# 添加信任命令
add_trusted_command() {
    local cmd="$1"
    if [ -z "$cmd" ]; then
        echo -e "${RED}错误: 请提供命令前缀${NC}"
        echo "用法: $0 add <command_prefix>"
        exit 1
    fi
    
    # 备份原文件
    cp "$SETTINGS_FILE" "$SETTINGS_FILE.backup"
    
    # 添加命令（如果不存在）
    jq --arg cmd "$cmd" \
        'if (.["kiroAgent.trustedCommands"] | index($cmd)) then . 
         else .["kiroAgent.trustedCommands"] += [$cmd] end' \
        "$SETTINGS_FILE" > "$SETTINGS_FILE.tmp" && \
        mv "$SETTINGS_FILE.tmp" "$SETTINGS_FILE"
    
    echo -e "${GREEN}✅ 已添加: $cmd${NC}"
}

# 删除信任命令
remove_trusted_command() {
    local cmd="$1"
    if [ -z "$cmd" ]; then
        echo -e "${RED}错误: 请提供命令前缀${NC}"
        echo "用法: $0 remove <command_prefix>"
        exit 1
    fi
    
    # 备份原文件
    cp "$SETTINGS_FILE" "$SETTINGS_FILE.backup"
    
    # 删除命令
    jq --arg cmd "$cmd" \
        '.["kiroAgent.trustedCommands"] -= [$cmd]' \
        "$SETTINGS_FILE" > "$SETTINGS_FILE.tmp" && \
        mv "$SETTINGS_FILE.tmp" "$SETTINGS_FILE"
    
    echo -e "${GREEN}✅ 已删除: $cmd${NC}"
}

# 清空所有信任命令
clear_all() {
    echo -e "${YELLOW}警告: 这将清空所有信任命令!${NC}"
    read -p "确认继续? (y/N): " confirm
    if [ "$confirm" = "y" ] || [ "$confirm" = "Y" ]; then
        cp "$SETTINGS_FILE" "$SETTINGS_FILE.backup"
        jq '.["kiroAgent.trustedCommands"] = []' \
            "$SETTINGS_FILE" > "$SETTINGS_FILE.tmp" && \
            mv "$SETTINGS_FILE.tmp" "$SETTINGS_FILE"
        echo -e "${GREEN}✅ 已清空所有信任命令${NC}"
    else
        echo "已取消"
    fi
}

# 恢复备份
restore_backup() {
    if [ -f "$SETTINGS_FILE.backup" ]; then
        cp "$SETTINGS_FILE.backup" "$SETTINGS_FILE"
        echo -e "${GREEN}✅ 已恢复备份${NC}"
    else
        echo -e "${RED}错误: 备份文件不存在${NC}"
    fi
}

# 主菜单
case "$1" in
    list|show)
        show_trusted_commands
        ;;
    add)
        add_trusted_command "$2"
        ;;
    remove|delete)
        remove_trusted_command "$2"
        ;;
    clear)
        clear_all
        ;;
    restore)
        restore_backup
        ;;
    *)
        echo "Kiro 信任命令管理工具"
        echo ""
        echo "用法:"
        echo "  $0 list                    # 显示当前信任列表"
        echo "  $0 add <command>           # 添加信任命令"
        echo "  $0 remove <command>        # 删除信任命令"
        echo "  $0 clear                   # 清空所有信任命令"
        echo "  $0 restore                 # 恢复备份"
        echo ""
        echo "示例:"
        echo "  $0 list"
        echo "  $0 add 'black*'"
        echo "  $0 remove 'rm*'"
        ;;
esac
