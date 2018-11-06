function _luna_autocomplete() {
    compopt +o bashdefault +o default +o dirnames +o filenames +o nospace +o plusdirs
    local CUR=${COMP_WORDS[COMP_CWORD]}
    if [ ${COMP_CWORD} -eq 1 ]; then
        local LUNA_OBJECTS=$(luna -h | sed -n '/positional arguments:/{n;s/[{},]/ /g;p}' 2>/dev/null)
        COMPREPLY=($(compgen -W "${LUNA_OBJECTS}" -- ${CUR}))
        return 0
    fi
    if [ ${COMP_CWORD} -eq 2 ]; then
        local LUNA_OBJECT=${COMP_WORDS[COMP_CWORD-1]}
        local LUNA_OPERATIONS=$(luna ${LUNA_OBJECT} -h | sed -n '/positional arguments:/{n;s/[{},]/ /g;p}' 2>/dev/null)
        COMPREPLY=($(compgen -W "${LUNA_OPERATIONS}" -- ${CUR}))
        return 0
    fi
    if [ ${COMP_CWORD} -eq 3 ]; then
        local LUNA_OBJECT=${COMP_WORDS[COMP_CWORD-2]}
        if ! [ ${COMP_WORDS[2]} = "add" -o ${COMP_WORDS[2]} = "list" -o ${LUNA_OBJECT} = "cluster" ]; then
            OBJECTS=$(python -c "import luna; print \" \".join(luna.list(\"${LUNA_OBJECT}\"))" 2>/dev/null)
            COMPREPLY=($(compgen -W "${OBJECTS}" -- ${CUR}))
            return 0
        fi
    fi
    local LUNA_OBJECT=${COMP_WORDS[1]}
    local LUNA_OPERATION=${COMP_WORDS[2]}
    local PREV=${COMP_WORDS[COMP_CWORD-1]}
    if [ ${LUNA_OBJECT} = "node" -a ${LUNA_OPERATION} = "add" -o ${LUNA_OPERATION} = "change" ]; then
        case "${PREV}" in
            --group|-g)
                LUNA_GROUPS=$(python -c "import luna; print \" \".join(luna.list(\"group\"))" 2>/dev/null)
                COMPREPLY=($(compgen -W "${LUNA_GROUPS}" -- ${CUR}))
                return 0
                ;;
        esac
    fi
    if [ ${LUNA_OBJECT} = "node" -a ${LUNA_OPERATION} = "list" ]; then
        case "${PREV}" in
            --group|-g)
                LUNA_GROUPS=$(python -c "import luna; print \" \".join(luna.list(\"group\"))" 2>/dev/null)
                COMPREPLY=($(compgen -W "${LUNA_GROUPS}" -- ${CUR}))
                return 0
                ;;
        esac
    fi
    if [ ${LUNA_OBJECT} = "node" -a ${LUNA_OPERATION} = "change" ]; then
        case "${PREV}" in
            --switch|-s)
                LUNA_SWITCHES=$(python -c "import luna; print \" \".join(luna.list(\"switch\"))" 2>/dev/null)
                COMPREPLY=($(compgen -W "${LUNA_SWITCHES}" -- ${CUR}))
                return 0
                ;;
            --localboot|-l|--setupbmc|--sb|--service|--sv)
                COMPREPLY=($(compgen -W "y n" -- ${CUR}))
                return 0
                ;;
        esac
    fi
    if [ ${LUNA_OBJECT} = "group" -a ${LUNA_OPERATION} = "add" -o ${LUNA_OPERATION} = "change" ]; then
        case "${PREV}" in
            --osimage|-o)
                LUNA_OSIMAGES=$(python -c "import luna; print \" \".join(luna.list(\"osimage\"))" 2>/dev/null)
                COMPREPLY=($(compgen -W "${LUNA_OSIMAGES}" -- ${CUR}))
                return 0
                ;;
            --bmcsetup|-b)
                LUNA_BMCSETUPS=$(python -c "import luna; print \" \".join(luna.list(\"bmcsetup\"))" 2>/dev/null)
                COMPREPLY=($(compgen -W "${LUNA_BMCSETUPS}" -- ${CUR}))
                return 0
                ;;
            --bmcnetwork|--bn)
                LUNA_NETWORKS=$(python -c "import luna; print \" \".join(luna.list(\"network\"))" 2>/dev/null)
                COMPREPLY=($(compgen -W "${LUNA_NETWORKS}" -- ${CUR}))
                return 0
                ;;
        esac
    fi
    if [ ${LUNA_OBJECT} = "group" -a ${LUNA_OPERATION} = "change" ]; then
        case "${PREV}" in
            --setnet|--sn)
                LUNA_NETWORKS=$(python -c "import luna; print \" \".join(luna.list(\"network\"))" 2>/dev/null)
                COMPREPLY=($(compgen -W "${LUNA_NETWORKS}" -- ${CUR}))
                return 0
                ;;
        esac
    fi
    if [ ${LUNA_OBJECT} = "osimage" ]; then
        case "${PREV}" in
            --path|-p)
                compopt -o bashdefault -o default -o dirnames -o filenames -o nospace -o plusdirs
                return 0
                ;;
        esac
    fi
    if [ ${LUNA_OBJECT} = "otherdev" -a ${LUNA_OPERATION} = "change" -o ${LUNA_OPERATION} = "add" ]; then
        case "${PREV}" in
            --network|-N)
                LUNA_NETWORKS=$(python -c "import luna; print \" \".join(luna.list(\"network\"))" 2>/dev/null)
                COMPREPLY=($(compgen -W "${LUNA_NETWORKS}" -- ${CUR}))
                return 0
                ;;
        esac
    fi
    if [ ${LUNA_OBJECT} = "switch" -a ${LUNA_OPERATION} = "change" -o ${LUNA_OPERATION} = "add" ]; then
        case "${PREV}" in
            --network|-N)
                LUNA_NETWORKS=$(python -c "import luna; print \" \".join(luna.list(\"network\"))" 2>/dev/null)
                COMPREPLY=($(compgen -W "${LUNA_NETWORKS}" -- ${CUR}))
                return 0
                ;;
        esac
    fi
    LUNA_OPTS=$(luna ${LUNA_OBJECT} ${LUNA_OPERATION} -h | sed -e '1,/optional arguments:/{d};' -e 's/,/\n/; s/ /\n/g' | sed -n '/^-/p' 2>/dev/null)
    COMPREPLY=($(compgen -W "${LUNA_OPTS}" -- ${CUR}))
    return 0
}
function _lchroot_autocomplete() {
    compopt +o bashdefault +o default +o dirnames +o filenames +o nospace +o plusdirs
    local CUR=${COMP_WORDS[COMP_CWORD]}
    LUNA_OSIMAGES=$(python -c "import luna; print \" \".join(luna.list(\"osimage\"))" 2>/dev/null)
    COMPREPLY=($(compgen -W "${LUNA_OSIMAGES}" -- ${CUR}))
    return 0
}
complete -F _luna_autocomplete luna
complete -F _lchroot_autocomplete lchroot
