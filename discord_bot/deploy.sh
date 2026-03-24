#!/bin/bash

###############################################################################
# NEXO Discord Bot - Script de Despliegue
# Automatiza la instalación, configuración e inicio del bot
###############################################################################

set -e

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Funciones de utilidad
print_header() {
    echo -e "\n${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}\n"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

# Verificar requisitos
check_requirements() {
    print_header "Verificando Requisitos"

    # Verificar Node.js
    if ! command -v node &> /dev/null; then
        print_error "Node.js no está instalado"
        echo "Descarga desde: https://nodejs.org/"
        exit 1
    fi
    
    NODE_VERSION=$(node -v)
    print_success "Node.js $NODE_VERSION encontrado"

    # Verificar npm
    if ! command -v npm &> /dev/null; then
        print_error "npm no está instalado"
        exit 1
    fi
    
    NPM_VERSION=$(npm -v)
    print_success "npm $NPM_VERSION encontrado"

    # Verificar directorio
    if [ ! -f "bot.js" ]; then
        print_error "bot.js no encontrado. Asegúrate de estar en el directorio discord_bot/"
        exit 1
    fi
    print_success "Directorio correcto"
}

# Configurar variables de entorno
setup_env() {
    print_header "Configurando Variables de Entorno"

    if [ ! -f ".env" ]; then
        if [ ! -f ".env.example" ]; then
            print_error ".env.example no encontrado"
            exit 1
        fi

        print_info "Creando .env desde .env.example..."
        cp .env.example .env
        print_success ".env creado"

        print_warning "Por favor, edita .env con tus valores:"
        print_info "  - DISCORD_TOKEN"
        print_info "  - DISCORD_CLIENT_ID"
        print_info "  - NEXO_BACKEND"
        print_info "  - NEXO_API_KEY"
        
        echo ""
        read -p "¿Deseas editar .env ahora? (y/n) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            ${EDITOR:-nano} .env
        fi
    else
        print_success ".env ya existe"
    fi

    # Verificar variables críticas
    if ! grep -q "DISCORD_TOKEN=" .env || grep "DISCORD_TOKEN=your_bot_token_here" .env > /dev/null; then
        print_error "DISCORD_TOKEN no está configurado en .env"
        exit 1
    fi

    if ! grep -q "DISCORD_CLIENT_ID=" .env || grep "DISCORD_CLIENT_ID=your_client_id_here" .env > /dev/null; then
        print_error "DISCORD_CLIENT_ID no está configurado en .env"
        exit 1
    fi

    print_success "Variables de entorno verificadas"
}

# Instalar dependencias
install_dependencies() {
    print_header "Instalando Dependencias"

    if [ -d "node_modules" ]; then
        print_info "node_modules ya existe"
        read -p "¿Reinstalar dependencias? (y/n) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            rm -rf node_modules package-lock.json
        else
            print_success "Usando dependencias existentes"
            return
        fi
    fi

    print_info "Ejecutando npm install..."
    npm install

    print_success "Dependencias instaladas"
}

# Crear directorios necesarios
create_directories() {
    print_header "Creando Directorios"

    mkdir -p logs
    mkdir -p handlers
    mkdir -p data

    print_success "Directorios creados"
}

# Verificar conexión al backend
test_backend() {
    print_header "Probando Conexión al Backend"

    BACKEND_URL=$(grep "NEXO_BACKEND=" .env | cut -d '=' -f 2)
    
    if [ -z "$BACKEND_URL" ]; then
        BACKEND_URL="http://127.0.0.1:8000"
    fi

    print_info "Probando: $BACKEND_URL"

    if command -v curl &> /dev/null; then
        if curl -s "$BACKEND_URL/health" > /dev/null 2>&1; then
            print_success "Backend está online"
        else
            print_warning "Backend no responde (puede estar offline)"
            print_info "El bot intentará conectar cuando se inicie"
        fi
    else
        print_warning "curl no disponible, saltando test de backend"
    fi
}

# Iniciar bot
start_bot() {
    print_header "Iniciando Bot"

    print_info "Ejecutando: npm start"
    print_info "El bot se iniciará en unos segundos..."
    echo ""

    npm start
}

# Menú principal
show_menu() {
    echo ""
    echo -e "${BLUE}NEXO Discord Bot - Menú de Despliegue${NC}"
    echo "1. Instalación completa (recomendado para primera vez)"
    echo "2. Solo instalar dependencias"
    echo "3. Solo configurar variables de entorno"
    echo "4. Probar conexión al backend"
    echo "5. Iniciar bot"
    echo "6. Salir"
    echo ""
    read -p "Selecciona una opción (1-6): " option
}

# Main
main() {
    clear
    
    echo -e "${BLUE}"
    echo "╔════════════════════════════════════════╗"
    echo "║   NEXO Discord Bot - Deploy Script     ║"
    echo "║   El Anarcocapital Control Hub         ║"
    echo "╚════════════════════════════════════════╝"
    echo -e "${NC}"

    if [ $# -eq 0 ]; then
        # Modo interactivo
        while true; do
            show_menu
            case $option in
                1)
                    check_requirements
                    create_directories
                    setup_env
                    install_dependencies
                    test_backend
                    print_header "Instalación Completada"
                    print_success "El bot está listo para iniciar"
                    read -p "¿Deseas iniciar el bot ahora? (y/n) " -n 1 -r
                    echo
                    if [[ $REPLY =~ ^[Yy]$ ]]; then
                        start_bot
                    fi
                    ;;
                2)
                    check_requirements
                    install_dependencies
                    ;;
                3)
                    check_requirements
                    setup_env
                    ;;
                4)
                    check_requirements
                    test_backend
                    ;;
                5)
                    check_requirements
                    start_bot
                    ;;
                6)
                    print_info "Saliendo..."
                    exit 0
                    ;;
                *)
                    print_error "Opción inválida"
                    ;;
            esac
        done
    else
        # Modo línea de comandos
        case $1 in
            install)
                check_requirements
                create_directories
                setup_env
                install_dependencies
                test_backend
                print_success "Instalación completada"
                ;;
            start)
                start_bot
                ;;
            test)
                test_backend
                ;;
            *)
                echo "Uso: $0 [install|start|test]"
                exit 1
                ;;
        esac
    fi
}

main "$@"
