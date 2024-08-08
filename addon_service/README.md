# addon_service: a django app for the gravyvalet web api

## network flows

addon operation invocation thru gravyvalet (as currently implemented with osf)
```mermaid
sequenceDiagram
    participant browser
    Box *.osf.io
        participant gravyvalet
        participant osf-api
    end
    Note over browser: browsing files on osf, say
    browser->>gravyvalet: request directory listing (create an addon operation invocation)
    gravyvalet->>osf-api: who is this?
    osf-api->>gravyvalet: this is who
    Note over gravyvalet: gravyvalet asks "who is?" (auth-entic-ation) separate from "may they?" (auth-oriz-ation)
    gravyvalet->>osf-api: may they access this directory listing?
    alt no
        osf-api->>gravyvalet: no
        gravyvalet->>browser: no
    else yes
        osf-api->>gravyvalet: yes
        gravyvalet->>external-service: request directory listing
        external-service->>gravyvalet: serve directory listing
        Note over gravyvalet: listing translated into interoperable format
        gravyvalet->>browser: serve directory listing
    end
```

download a file thru waterbutler, with get_auth and gravyvalet (as currently implemented)
```mermaid
sequenceDiagram
    participant browser
    Box *.osf.io
        participant waterbutler
        participant osf-v1
        participant gravyvalet
    end
    browser->>waterbutler: request file
    waterbutler->>osf-v1: get_auth
    alt no
        osf-v1->>waterbutler: no
        waterbutler->>browser: no
    else yes
        osf-v1->>gravyvalet: request gravy
        gravyvalet->>osf-v1: serve gravy
        osf-v1->>waterbutler: credentials and config
        waterbutler->>external service: request file
        external service->>waterbutler: serve file
        waterbutler->>browser: serve file
    end
```

hypothetical world where waterbutler talks to gravyvalet... is this better than get_auth?
```mermaid
sequenceDiagram
    participant browser
    Box *.osf.io
        participant waterbutler
        participant gravyvalet
        participant osf-api
    end
    browser->>waterbutler: request file
    waterbutler->>gravyvalet: request gravy
    gravyvalet->>osf-api: who is this?
    osf-api->>gravyvalet: this is who
    gravyvalet->>osf-api: may they do what they're asking to?
    alt no
        osf-api->>gravyvalet: no
        gravyvalet->>waterbutler: no
        waterbutler->>browser: no
    else yes
        osf-api->>gravyvalet: yes
        gravyvalet->>waterbutler: serve gravy
        waterbutler->>external service: request file
        external service->>waterbutler: serve file
        waterbutler->>browser: serve file
    end
```
