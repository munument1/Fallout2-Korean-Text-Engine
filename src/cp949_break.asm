.386
.model flat
.code
; EAX: NUL-terminated text. Return final space (except initial position),
; otherwise the final complete CP949 character. Preserve caller registers.
; Input must be CP949. This fixes the legacy backwards high-byte heuristic.
cp949_break PROC
 push ecx
 push edx
 push ebx
 push esi
 mov esi,eax
 mov edx,eax
 xor eax,eax
 xor ebx,ebx
scan:
 mov cl,[edx]
 test cl,cl
 jz done
 mov eax,edx
 cmp cl,20h
 jne advance
 cmp edx,esi
 je advance
 mov ebx,edx
advance:
 inc edx
 cmp cl,81h
 jb scan
 cmp cl,0feh
 ja scan
 cmp byte ptr [edx],0
 je done
 inc edx
 jmp scan
done:
 test ebx,ebx
 jz restore
 mov eax,ebx
restore:
 pop esi
 pop ebx
 pop edx
 pop ecx
 ret
cp949_break ENDP
END
