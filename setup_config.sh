#!/usr/bin/env bash
# ══════════════════════════════════════════════════════════════════
#  setup_config.sh — Cấu hình & validate hệ thống RAG
#  Dùng: bash setup_config.sh [--validate-only]
# ══════════════════════════════════════════════════════════════════

set -uo pipefail

CONFIG_FILE="config.py"
PYTHON_BIN="${PYTHON:-python3}"

# ── Màu sắc ────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; DIM='\033[2m'; RESET='\033[0m'

info()    { echo -e "${CYAN}[INFO]${RESET}  $*"; }
success() { echo -e "${GREEN}[OK]${RESET}    $*"; }
warn()    { echo -e "${YELLOW}[WARN]${RESET}  $*"; }
error()   { echo -e "${RED}[ERR]${RESET}   $*"; }
header()  { echo -e "\n${BOLD}${CYAN}══ $* ══${RESET}"; }

# ── Đọc giá trị hiện tại từ config.py ─────────────────────────────
get_current_value() {
    local key="$1"
    grep -E "^${key}\s*=" "$CONFIG_FILE" \
        | head -1 \
        | sed -E 's/^[^=]+=\s*"?([^"#]+)"?.*/\1/' \
        | tr -d '[:space:]'
}

# ── Kiểm tra Python ────────────────────────────────────────────────
check_python() {
    if ! command -v "$PYTHON_BIN" &>/dev/null; then
        error "Không tìm thấy Python. Đặt biến PYTHON hoặc cài python3."
        exit 1
    fi
    success "Python: $($PYTHON_BIN --version)"
}

# ── Kiểm tra config.py tồn tại ────────────────────────────────────
check_config_exists() {
    if [[ ! -f "$CONFIG_FILE" ]]; then
        error "Không tìm thấy $CONFIG_FILE trong thư mục hiện tại: $(pwd)"
        exit 1
    fi
    success "Tìm thấy $CONFIG_FILE"
}

# ── Chạy validate() trong Python ──────────────────────────────────
run_validate() {
    header "Chạy validate()"
    "$PYTHON_BIN" - <<PYEOF
import sys, os
sys.path.insert(0, os.getcwd())
if 'config' in sys.modules:
    del sys.modules['config']
try:
    import config
    config.validate()
    print("\033[0;32m[OK]\033[0m    validate() PASSED")
except Exception as e:
    print(f"\033[0;31m[ERR]\033[0m   validate() FAILED: {e}")
    sys.exit(1)
PYEOF
}

# ── Ghi giá trị vào config.py ─────────────────────────────────────
set_config_value() {
    local key="$1" value="$2" is_string="$3"
    if [[ "$is_string" == "1" ]]; then
        sed -i.bak -E "s|^(${key}\s*=).*|\1 \"${value}\"|" "$CONFIG_FILE"
    else
        sed -i.bak -E "s|^(${key}\s*=).*|\1 ${value}|" "$CONFIG_FILE"
    fi
    rm -f "${CONFIG_FILE}.bak"
}

# ══════════════════════════════════════════════════════════════════
#  pick_option — KHÔNG dùng subshell, lưu kết quả vào $PICKED
#  Cách gọi: pick_option "Prompt" "current_val" "opt1" "opt2" ...
# ══════════════════════════════════════════════════════════════════
PICKED=""
pick_option() {
    local prompt="$1"
    local current="$2"
    shift 2
    local options=("$@")
    local idx=1 ans found_current=0

    echo -e "${YELLOW}${prompt}${RESET}"
    for opt in "${options[@]}"; do
        if [[ "$opt" == "$current" ]]; then
            echo -e "  ${GREEN}${BOLD}$idx) $opt  ← hiện tại${RESET}"
            found_current=1
        else
            echo "  $idx) $opt"
        fi
        ((idx++))
    done

    if [[ $found_current -eq 0 && -n "$current" ]]; then
        echo -e "  ${DIM}(Hiện tại: \"$current\" — không có trong danh sách)${RESET}"
    fi

    while true; do
        if [[ -n "$current" ]]; then
            printf "Nhập số [1-%d] hoặc Enter để giữ nguyên: " "${#options[@]}"
        else
            printf "Nhập số [1-%d]: " "${#options[@]}"
        fi

        read -r ans </dev/tty

        if [[ -z "$ans" && -n "$current" ]]; then
            PICKED="$current"
            echo -e "  ${DIM}→ Giữ nguyên: ${current}${RESET}"
            return
        fi

        if [[ "$ans" =~ ^[0-9]+$ ]] && (( ans >= 1 && ans <= ${#options[@]} )); then
            PICKED="${options[$((ans-1))]}"
            return
        fi

        warn "Vui lòng nhập số từ 1 đến ${#options[@]}${current:+ hoặc Enter để giữ nguyên}."
    done
}

# ── Nhập số nguyên ────────────────────────────────────────────────
read_int() {
    local prompt="$1" default="$2" value
    while true; do
        printf "%s [hiện tại: %s]: " "$prompt" "$default"
        read -r value </dev/tty
        value="${value:-$default}"
        if [[ "$value" =~ ^[0-9]+$ ]]; then
            PICKED="$value"
            return
        fi
        warn "Vui lòng nhập số nguyên dương."
    done
}

# ── Hỏi hệ thống prompt ───────────────────────────────────────────
edit_system_prompt() {
    header "System Prompt"
    printf "Bạn có muốn chỉnh sửa SYSTEM_PROMPT không? [y/N]: "
    read -r ans </dev/tty
    if [[ "$ans" =~ ^[Yy]$ ]]; then
        local editor="${EDITOR:-nano}"
        if command -v "$editor" &>/dev/null; then
            info "Mở $CONFIG_FILE bằng $editor để chỉnh SYSTEM_PROMPT..."
            "$editor" "$CONFIG_FILE" </dev/tty
        else
            warn "Không tìm thấy editor '$editor'. Bỏ qua bước này."
            info "Bạn có thể sửa thủ công SYSTEM_PROMPT trong $CONFIG_FILE."
        fi
    fi
}

# ══════════════════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════════════════
main() {
    echo -e "${BOLD}${CYAN}"
    echo "╔══════════════════════════════════════════╗"
    echo "║     RAG Config Setup & Validator         ║"
    echo "╚══════════════════════════════════════════╝"
    echo -e "${RESET}"

    check_python
    check_config_exists

    # ── Chế độ chỉ validate ───────────────────────────────────────
    if [[ "${1:-}" == "--validate-only" ]]; then
        if run_validate; then
            success "Cấu hình hợp lệ."
        else
            error "Cấu hình không hợp lệ."
            exit 1
        fi
        exit 0
    fi

    # ══════════════════════════════════════════════════════════════
    #  1. EMBEDDING PROVIDER
    # ══════════════════════════════════════════════════════════════
    header "Embedding Provider"
    CUR_EMBED=$(get_current_value "EMBED_PROVIDER")
    pick_option "Chọn Embedding Provider:" "$CUR_EMBED" \
        "local" "openai"
    EMBED_PROVIDER="$PICKED"
    set_config_value "EMBED_PROVIDER" "$EMBED_PROVIDER" 1
    success "EMBED_PROVIDER = $EMBED_PROVIDER"

    if [[ "$EMBED_PROVIDER" == "local" ]]; then
        header "Local Embedding Model"
        CUR_LOCAL=$(get_current_value "EMBED_MODEL_LOCAL")
        pick_option "Chọn model local:" "$CUR_LOCAL" \
            "paraphrase-multilingual-MiniLM-L12-v2" \
            "all-MiniLM-L6-v2" \
            "all-mpnet-base-v2"
        set_config_value "EMBED_MODEL_LOCAL" "$PICKED" 1
        success "EMBED_MODEL_LOCAL = $PICKED"
    else
        header "OpenAI Embedding Model"
        CUR_OAI_EMBED=$(get_current_value "EMBED_MODEL_OPENAI")
        pick_option "Chọn model OpenAI embedding:" "$CUR_OAI_EMBED" \
            "text-embedding-3-small" \
            "text-embedding-3-large" \
            "text-embedding-ada-002"
        set_config_value "EMBED_MODEL_OPENAI" "$PICKED" 1
        success "EMBED_MODEL_OPENAI = $PICKED"
    fi

    # ══════════════════════════════════════════════════════════════
    #  2. LLM PROVIDER
    # ══════════════════════════════════════════════════════════════
    header "LLM Provider"
    CUR_LLM=$(get_current_value "LLM_PROVIDER")
    pick_option "Chọn LLM Provider:" "$CUR_LLM" \
        "deepseek" "openai" "anthropic"
    LLM_PROVIDER="$PICKED"
    set_config_value "LLM_PROVIDER" "$LLM_PROVIDER" 1
    success "LLM_PROVIDER = $LLM_PROVIDER"

    # Đọc model hiện tại của provider được chọn từ dict LLM_MODELS
    CUR_LLM_MODEL=$("$PYTHON_BIN" - <<PYEOF
import re
content = open("$CONFIG_FILE").read()
m = re.search(r'"${LLM_PROVIDER}"\s*:\s*"([^"]+)"', content)
print(m.group(1) if m else "")
PYEOF
)

    header "LLM Model (${LLM_PROVIDER})"
    case "$LLM_PROVIDER" in
        openai)
            pick_option "Chọn OpenAI model:" "$CUR_LLM_MODEL" \
                "gpt-4o-mini" "gpt-4o" "gpt-3.5-turbo"
            ;;
        deepseek)
            pick_option "Chọn DeepSeek model:" "$CUR_LLM_MODEL" \
                "deepseek-chat" "deepseek-reasoner"
            ;;
        anthropic)
            pick_option "Chọn Anthropic model:" "$CUR_LLM_MODEL" \
                "claude-3-5-haiku-20241022" \
                "claude-3-5-sonnet-20241022" \
                "claude-3-opus-20240229"
            ;;
    esac
    LLM_MODEL="$PICKED"
    sed -i.bak -E "s|(\"${LLM_PROVIDER}\"\s*:\s*)\"[^\"]+\"|\1\"${LLM_MODEL}\"|" "$CONFIG_FILE"
    rm -f "${CONFIG_FILE}.bak"
    success "LLM_MODEL (${LLM_PROVIDER}) = $LLM_MODEL"

    # ══════════════════════════════════════════════════════════════
    #  3. CHUNK CONFIG
    # ══════════════════════════════════════════════════════════════
    header "Chunk Config"
    CUR_CHUNK=$(get_current_value "CHUNK_SIZE")
    read_int "CHUNK_SIZE (ký tự/chunk)" "${CUR_CHUNK:-1000}"
    set_config_value "CHUNK_SIZE" "$PICKED" 0
    CHUNK_SIZE_VAL="$PICKED"

    CUR_OVERLAP=$(get_current_value "OVERLAP")
    read_int "OVERLAP (ký tự overlap)" "${CUR_OVERLAP:-150}"
    set_config_value "OVERLAP" "$PICKED" 0
    success "CHUNK_SIZE=$CHUNK_SIZE_VAL  OVERLAP=$PICKED"

    # ══════════════════════════════════════════════════════════════
    #  4. QUERY CONFIG
    # ══════════════════════════════════════════════════════════════
    header "Query Config"
    CUR_TOPK=$(get_current_value "TOP_K")
    read_int "TOP_K (số chunks retrieve)" "${CUR_TOPK:-5}"
    set_config_value "TOP_K" "$PICKED" 0
    TOPK_VAL="$PICKED"

    CUR_MAXTOK=$(get_current_value "MAX_TOKENS")
    read_int "MAX_TOKENS (giới hạn token LLM)" "${CUR_MAXTOK:-1024}"
    set_config_value "MAX_TOKENS" "$PICKED" 0
    success "TOP_K=$TOPK_VAL  MAX_TOKENS=$PICKED"

    # ══════════════════════════════════════════════════════════════
    #  5. SYSTEM PROMPT (tuỳ chọn)
    # ══════════════════════════════════════════════════════════════
    edit_system_prompt

    # ══════════════════════════════════════════════════════════════
    #  VALIDATE
    # ══════════════════════════════════════════════════════════════
    if run_validate; then
        echo ""
        success "✓ Tất cả cấu hình đã được lưu và hợp lệ trong $CONFIG_FILE"
    else
        error "Có lỗi trong config. Kiểm tra lại $CONFIG_FILE."
        exit 1
    fi
}

main "$@"
