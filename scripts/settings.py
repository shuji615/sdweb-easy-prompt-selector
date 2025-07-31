from modules import script_callbacks, shared

def on_ui_settings():
    shared.opts.add_option("eps_enable_save_raw_prompt_to_pnginfo", shared.OptionInfo(False, "元プロンプトを pngninfo に保存する", section=("easy_prompt_selector", "EasyPromptSelector")))
    shared.opts.add_option("eps_show_current_combination", shared.OptionInfo(True, "現在の組合せ数を表示する", section=("easy_prompt_selector", "EasyPromptSelector")))
    shared.opts.add_option("eps_prompt_textbox_input", shared.OptionInfo(True, "現在の組合せ数を UI に表示する", section=("easy_prompt_selector", "EasyPromptSelector")))

script_callbacks.on_ui_settings(on_ui_settings)
