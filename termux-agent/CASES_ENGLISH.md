# Test Cases (CASES_ENGLISH.md)

| Date | Goal | Status | Model | Key Notes |
|---|---|---|---|---|
| 2026-05-10 | Search map for 'best pizza in SF', click Call, and return home | ✅ Success | gemma4:26b | Resolved the "Sisyphus loop", introduced state audit mechanism. |
| 2026-05-10 | Search browser for 'nvidia stock' | ✅ Success | gemma4:26b | Verified UI element sniffing enhancement and coordinate clicking. |
| 2026-05-10 | Set alarm for tomorrow at 08:00 and return home | ✅ Success | gemma4:26b | Verified defensive error reporting and self-correction for `id: null`. |
| 2026-05-10 | Search Starbucks on map, note address, and SMS it to the first contact | ✅ Success | gemma4:26b | Top-tier cross-app task. Overcame complex obstacles like login popups and empty contact lists (switched to new chat). |
| 2026-05-10 | Create new contact 'Test Agent' (18888888888) and save | ✅ Success | gemma4:26b | Overcame visual interference caused by Android phone number auto-formatting. |
| 2026-05-10 | Clock App: click 'Timer' tab and return home | ✅ Success | gemma4:e4b | Verified basic pipeline of the new remote model Gemma 4 e4b. |
| 2026-05-10 | Calculate '2026-1998' in browser and SMS result to 10086 | ❌ Failure | gemma4:e4b | **Data amnesia**. Model saw result '28' in browser, but lost the specific value when switching to SMS. |
| 2026-05-10 | (Retry) Calculate '2026-1998' in browser and SMS result to 10086 | ✅ Success | gemma4:e4b | **Cured amnesia**. Successfully maintained data flow via `scratchpad` cross-step memory mechanism. |
| 2026-05-10 | Check Android version in Settings and return home | ✅ Success | gemma4:e4b | Verified deep navigation, mis-touch correction (Cancel popup), and blind coordinate clicking. |
| 2026-05-10 | Search NVIDIA stock price and SMS to 12345 | ✅ Success | gemma4:e4b | **Ultimate correction**. Overcame text residue interference, verified the combined power of "1.0s focus wait" + "memory transfer". |
| 2026-05-10 | (Final Version) Search NVIDIA stock price and SMS to 12345 | ✅ Success | gemma4:e4b | Physically stable. After introducing `adb_type` focus wait, cross-app typing succeeded on the first try, perfect closed loop. |
| 2026-05-10 | Open new chat with '13800138000' and send verification code 9527 | ✅ Success | gemma4:e4b | **Door-pushing logic**. Conquered the UX trap of "must click suggestion to enter after typing number", combined with physical full clear to achieve zero-pollution sending. |

## Pending Issues
- **Cross-app data persistence**: Initially resolved via scratchpad, needs further stress testing.
- **Photos top-right blind spot**: Some highly customized UIs still have detector black holes.
- **UI refresh delay**: XML doesn't refresh in time after some interface switches, causing ID misalignment.

### Goal: Send SMS to 12345: Finally solved Chinese input
- **Status**: SUCCESS
- **Verification**: ADBKeyBoard successfully injected Chinese characters; verification step confirmed text appeared in message box.
- **Notes**: Chinese typing is now near-instant and reliable.

### Goal: Determine if typing+send relies on latest XML after IME pops up
- **Status**: ANALYSIS ONLY
- **Verification**: Inspected `humanoid_agent.py`; `adb_type` performs tap, clear, input, and optional `ADB_EDITOR_CODE` in one function without re-dumping UI XML between typing and editor action.
- **Notes**: No code change. Proposed verification should compare IME editor-action send against visual click send under intentionally stale XML after keyboard-induced layout change.

### Goal: Verify if ADB_EDITOR_CODE can send SMS directly with a minimal script
- **Status**: SUCCESS
- **Verification**: Ran `python3 tests/verify_ime_editor_send.py --to 10086`; it opened the existing 10086 thread, tapped the message input, used `ADB_INPUT_TEXT`, then sent only `ADB_EDITOR_CODE 4` without clicking a visual send button.
- **Notes**: Final screenshot showed sent bubble `IME_TEST_1778468351`, the input box returned to `Text message`, and the script reported `PASS: ADB_EDITOR_CODE send submitted the message without clicking a visual send button.`

### Goal: Document ADB_EDITOR_CODE SMS sending experience
- **Status**: SUCCESS
- **Verification**: Appended the verified field note to `CHALLENGES.md` under Challenge 14.
- **Notes**: The note explicitly distinguishes "send button was clicked" from the actual result: no visual send click happened; `ADB_EDITOR_CODE 4` submitted the focused SMS input directly.

```json
    true,
    true,
    true,
    true,
    false
  ],
  "notes_to_save": []
}
```

==================== STEP 5 [DECISION] [GEMMA] ====================
```json
{
  "thought": "Based on the task list and achievements so far, the SMS sending operation has been successfully completed. The current screen displays the chat interface within the SMS application, but the overall goal requires returning to the phone's home screen (desktop). Therefore, I need to execute the action to return to the home screen.",
  "action": "home",
  "id": null,
  "point": null,
  "text": "",
  "pkg": null,
  "seconds": 3
}
```

```json
  "notes_to_save": [
    "SMS content: Dear customer, your verification code is 9527, please do not disclose it."
  ]
}
```

==================== STEP 4 [DECISION] [GEMMA] ====================
```json
{
  "thought": "Based on the feedback from the previous step, the message content has been successfully entered into the SMS input box. Now I need to click the send button to complete the third step of the task (successful sending). Since the current screenshot doesn't directly show the ID of the send button, I must estimate the coordinates of the send button at the bottom of the standard Android SMS interface. The send button is expected to be located in the bottom right area of the screen; clicking this point will trigger the message sending operation.",
  "action": "click",
  "id": null,
  "point": [
    950,
    2350
  ],
  "text": null,
  "editor_action": null,
  "pkg": null,
  "seconds": 3
}
```
