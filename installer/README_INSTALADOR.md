# DisateQ Motor CPE v5.0 -- Guia del Instalador

Uso interno DisateQ DEV -- TASK-INS-01

---

## Prerequisitos

1. Ejecutar `.\build.ps1` -- genera `dist\DisateQ-Motor-CPE\`
2. Inno Setup 6 instalado -- https://jrsoftware.org/isdl.php
3. Config del cliente en `dist\DisateQ-Motor-CPE\config\`
4. `src\licenses\keys\disateq_public.pem` presente

---

## Generar instalador

```powershell
.\installer\build_installer.ps1 -Cliente farmacia_central
```

Resultado: `installer\Output\DisateQ-Motor-CPE-Setup.exe`

---

## Lo que hace el instalador en el equipo del cliente

### Pagina 1 -- Directorio del programa
- Default: `C:\Program Files\DisateQ\Motor CPE\`
- Instala: exe, _internal, config, licenses\disateq_public.pem
- Escribe: disateq_paths.cfg con las rutas resueltas

### Pagina 2 -- Directorio de datos
- Default: `D:\DisateQ\Data\`
- Crea: `data\` y `output\` en la ruta elegida por el cliente

---

## Estructura resultante

```
C:\Program Files\DisateQ\Motor CPE\
    DisateQ-Motor-CPE.exe
    _internal\
    config\
        clientes\{cliente}.yaml
        contratos\{cliente}.yaml
    licenses\
        disateq_public.pem
    disateq_paths.cfg

D:\DisateQ\Data\
    data\
        disateq_cpe.db
        disateq.log
    output\
        {ruc}\{tipo}\*.txt
```

---

## Entrega al cliente

| Elemento | Como |
|---|---|
| DisateQ-Motor-CPE-Setup.exe | Descarga / USB / Drive |
| disateq_motor.lic | Email separado |

El cliente carga la licencia desde Config UI: boton "Cargar licencia (.lic)"

---

## Reglas de seguridad

- disateq_private.pem -- NUNCA incluir en el instalador
- disateq_cpe.db -- NO preinstalar, se genera en runtime
- El desinstalador NO borra la carpeta de datos en D:
