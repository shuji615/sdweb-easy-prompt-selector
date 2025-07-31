from pathlib import Path
import random
import re
import yaml
import gradio as gr

import modules.scripts as scripts
from modules.scripts import AlwaysVisible, basedir
from modules import shared
# from scripts.setup import write_filename_list # この行は元のままでOKですが、もし write_filename_list が未定義ならコメントアウトまたは適切に修正してください

FILE_DIR = Path().absolute()
BASE_DIR = Path(basedir())
TAGS_DIR = BASE_DIR.joinpath('tags')

def tag_files():
    return TAGS_DIR.rglob("*.yml")

def load_tags():
    tags = {}
    for filepath in tag_files():
        with open(filepath, "r", encoding="utf-8") as file:
            yml = yaml.safe_load(file)
            tags[filepath.stem] = yml
    return tags

def find_tag_options(tags, location):
    if type(location) == str:
        if location not in tags:
            return [f"Error: tag '{location}' not found"]
        tag_data = tags[location]
    else:
        tag_data = tags
        for tag in location:
            if tag not in tag_data:
                return [f"Error: tag '{':'.join(location)}' not found at '{tag}'"]
            tag_data = tag_data[tag]

    def get_options(data):
        options = []
        if isinstance(data, dict):
            for key, value in data.items():
                if isinstance(value, dict) or isinstance(value, list):
                    options.extend(get_options(value))
                else:
                    options.append(value)
        elif isinstance(data, list):
            options.extend(data)
        else:
            options.append(data)
        return options

    options = get_options(tag_data)
    if not options:
        return [f"Error: no options found for tag '{':'.join(location) if isinstance(location, list) else location}'"]
    return list(options)


def parse_template(template_match):
    template = template_match.group()
    num_str = template_match.group('num')
    ref = template_match.group('ref')

    min_count, max_count = 1, 1
    if num_str:
        try:
            result = list(map(lambda x: int(x), num_str.split('-')))
            min_count = min(result)
            max_count = max(result)
        except Exception:
            pass

    return {
        'template': template,
        'ref': ref.split(':'),
        'min_count': min_count,
        'max_count': max_count,
    }

def calculate_combinations_count(tags, prompt):
    if not '@' in prompt:
        return 1

    parsed_templates = [parse_template(match) for match in re.finditer(r'(@((?P<num>\d+(-\d+)?)\$\$)?(?P<ref>[^>]+?)@)', prompt)]
    total_combinations = 1

    for template_info in parsed_templates:
        tag_options_list = find_tag_options(tags, template_info['ref'])
        if "Error:" in tag_options_list[0]:
            return "Error: " + tag_options_list[0]

        counts = range(template_info['min_count'], template_info['max_count'] + 1)
        template_combinations = 0

        for count in counts:
            if len(tag_options_list) < count:
                return f"Error: not enough tags for '{template_info['ref']}' (requested {count}, but only {len(tag_options_list)} available)"
            
            def get_tag_combinations_count(options_count, num_tags):
                if num_tags == 0:
                    return 1
                # 変更: 組み合わせではなく、各位置で独立して選択する場合 (重複あり)
                # return options_count ** num_tags 
                # もし重複なしの組み合わせ (nCr) を意図している場合は、math.comb を使う必要があるが、
                # この文脈ではタグの選択肢から選ぶので、重複ありで良いか、
                # あるいは「異なるタグをN個選ぶ」なので、重複なし順列 (nPr) や組み合わせ (nCr) か。
                # 元のコードは options_count ** num_tags なので、重複を許す選択と解釈。
                # ここでは元のロジックを維持。
                if num_tags < 0: return 0 #念のため
                if num_tags == 0: return 1
                if options_count < num_tags and template_info['min_count'] == template_info['max_count']: # 選択肢より多く選ぶことはできない（重複なしの場合）
                     # ただし、元のコードは options_count ** num_tags なので、これは重複を許す前提。
                     # このチェックは重複なしの場合に意味がある。元のロジックに合わせて一旦コメントアウト。
                     # return f"Error: not enough unique tags for '{template_info['ref']}' (requested {count}, but only {len(tag_options_list)} available for unique selection)"
                     pass


                # 単純なべき乗で良いか、それとも options_count から num_tags を選ぶ組み合わせか。
                # タグのリストから `count` 個選ぶ、という文脈であれば、
                # もし「同じタグを複数回使っても良い」なら options_count ** count
                # もし「異なるタグを count 個選ぶ」なら、それは組み合わせの数 (nCr) や順列の数 (nPr)。
                # generate_combinations の実装を見ると、get_tag_combinations は重複を許してタグを選んでいるように見える。
                # (options をループし、再帰的に num_tags-1 で呼び出している)
                # そのため、 options_count ** num_tags が意図した計算である可能性が高い。
                
                # get_tag_combinations_count のロジックは元のままとする
                if num_tags == 0:
                    return 1
                return options_count ** num_tags


            template_combinations += get_tag_combinations_count(len(tag_options_list), count)

        if template_combinations == 0 and template_info['min_count'] > 0 : # 組み合わせが0だが、最低1つは選ぶはずだった場合
             # このケースは上の len(tag_options_list) < count で捕捉されるはず
             pass

        total_combinations *= template_combinations
        if total_combinations == 0 and template_info['min_count'] > 0: # 途中で組み合わせが0になったら、それ以上計算しても0
            break


    return total_combinations


def generate_combinations(tags, parsed_templates):
    all_combinations = []

    def recursive_combination(current_combination, template_index):
        if template_index == len(parsed_templates):
            all_combinations.append(list(current_combination))
            return

        template_info = parsed_templates[template_index]
        tag_options_list = find_tag_options(tags, template_info['ref'])
        if "Error:" in tag_options_list[0]:
            # エラーがある場合、残りのテンプレートについてもエラー情報を伝播させるか、ここで処理を打ち切るか。
            # ここでは、エラーがあったテンプレート以降は処理せず、エラー情報を含む組み合わせを生成する。
            remaining_templates = len(parsed_templates) - template_index
            all_combinations.append(list(current_combination) + [tag_options_list[0]] * remaining_templates)
            return


        counts = range(template_info['min_count'], template_info['max_count'] + 1)
        
        # このテンプレートで有効な組み合わせが生成されるかのフラグ
        generated_for_this_template = False

        for count_val in counts: # count は Python の組み込み関数と名前が衝突するので count_val に変更
            if len(tag_options_list) < count_val and count_val > 0 : # 重複なしで選ぶならこのチェックは重要
                # ただし、現在の get_tag_combinations は重複を許す実装になっている。
                # もし重複を許すなら、len(tag_options_list) が count_val より小さくても問題ない。
                # (例: 選択肢 [A, B] から 3つ選ぶ -> AAA, AAB, ABA, ABB, BAA, BAB, BBA, BBB)
                # ここでは、元のコードの挙動（エラーメッセージを返す）を尊重し、
                # 「十分なタグがない」というエラーを返すようにする。
                # ただし、このエラーは find_tag_options や calculate_combinations_count で先に捕捉されるべき。
                # generate_combinations までエラーが素通りしている場合、それを処理する。
                # recursive_combination(current_combination + [f"Error: not enough tags for '{template_info['ref']}' (requested {count_val}, but only {len(tag_options_list)} available)"] * count_val, template_index + 1)
                # continue # 次の count_val へ
                pass # calculate_combinations_count でエラー処理されているはずなので、ここでは何もしないか、エラーを伝播

            def get_tag_combinations(options, current_tags_list, num_tags_to_select):
                if num_tags_to_select == 0:
                    yield list(current_tags_list)
                    return

                if not options: # 選択肢がない場合は何も生成できない
                    if num_tags_to_select > 0: # タグを選ぶ必要があるのに選択肢がない
                         yield [f"Error: No options to select {num_tags_to_select} tags for '{template_info['ref']}'"] * num_tags_to_select
                    return

                for option in options:
                    yield from get_tag_combinations(options, current_tags_list + [option], num_tags_to_select - 1)
            
            for tags_combination in get_tag_combinations(tag_options_list, [], count_val):
                if any("Error:" in tc for tc in tags_combination if isinstance(tc, str)): # エラーが含まれる組み合わせはスキップまたは処理
                     recursive_combination(current_combination + tags_combination, template_index + 1)
                else:
                     recursive_combination(current_combination + [', '.join(tags_combination)], template_index + 1)
                generated_for_this_template = True
        
        if not generated_for_this_template and template_info['min_count'] > 0:
            # このテンプレートで何も組み合わせが生成されなかったが、最低1つは必要だった場合
            # (例: 範囲が0-0で、min_countが1など、通常は発生しにくいが念のため)
            recursive_combination(current_combination + [f"Error: No combinations generated for '{template_info['ref']}' with count range {template_info['min_count']}-{template_info['max_count']}"], template_index + 1)


    recursive_combination([], 0)
    return all_combinations

def replace_template_random(tags, prompt, seed = None):
    if seed is not None: # seedがNoneでない場合のみ設定
      random.seed(seed)

    # count はループカウンタなので、max_iterations などに名前変更を推奨
    max_iterations = 100 
    current_iter = 0
    while current_iter < max_iterations:
        if not '@' in prompt:
            break

        # 変更箇所を記録しておき、一度のイテレーションで複数のテンプレートを置換する
        # finditer はイミュータブルな文字列に対して動作するので、置換ごとに再検索が必要
        # または、一度にすべてのマッチを取得し、後ろから置換していく
        
        match = re.search(r'(@((?P<num>\d+(-\d+)?)\$\$)?(?P<ref>[^>]+?)@)', prompt)
        if not match:
            break # マッチがなくなったらループ終了

        template = match.group()
        num_str = match.group('num')
        ref_str = match.group('ref')

        min_count_choice, max_count_choice = 1, 1
        if num_str:
            try:
                result = list(map(lambda x: int(x), num_str.split('-')))
                min_count_choice = min(result)
                max_count_choice = max(result)
            except Exception: # pylint: disable=broad-except
                pass # エラーの場合はデフォルト値(1,1)を使用

        num_to_select = random.randint(min_count_choice, max_count_choice)
        
        selected_tags = []
        has_error = False
        for _ in range(num_to_select):
            options = find_tag_options(tags, ref_str.split(':'))
            if options and "Error:" in options[0]:
                selected_tags.append(options[0]) # エラーメッセージを追加
                has_error = True
                break # 一つでもエラーがあれば、このテンプレートの処理は中断
            elif options:
                selected_tags.append(random.choice(options))
            else: # options が空 (エラーでもない)
                selected_tags.append(f"Error: No options for {ref_str}")
                has_error = True
                break
        
        replacement = ', '.join(selected_tags)
        prompt = prompt.replace(template, replacement, 1)

        current_iter += 1

    if seed is not None: # 処理後にグローバルのseed状態をリセット
        random.seed() # 引数なしでシステム時間などで初期化
    return prompt


class Script(scripts.Script):
    tags = {}
    combinations = []
    current_combination_index = 0
    previous_prompt = None
    selection_mode = "random"

    def __init__(self):
        super().__init__()
        self.tags = load_tags()
        # setup.py と同じディレクトリに配置された write_filename_list を安全に呼び出す
        try:
            import importlib.util, sys, pathlib
            setup_path = pathlib.Path(__file__).with_name('setup.py')
            spec = importlib.util.spec_from_file_location('eps_setup', setup_path)
            if spec and spec.loader:
                setup_mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(setup_mod)
                if hasattr(setup_mod, 'write_filename_list') and callable(setup_mod.write_filename_list):
                    setup_mod.write_filename_list()
        except Exception as e:
            print(f"EasyPromptSelector: failed to execute write_filename_list in __init__: {e}")


    def title(self):
        return "EasyPromptSelector Round Robin or Random"

    def show(self, is_img2img):
        return AlwaysVisible

    def ui(self, is_img2img):
        if (is_img2img):
            return None

        # 組み合わせ数を計算して表示する関数
        def _update_combination_count_display(prompt_text):
            if not hasattr(self, 'tags') or not self.tags: # tagsがロードされていない場合
                self.tags = load_tags() #念のためロード
            
            count = calculate_combinations_count(self.tags, prompt_text)
            if isinstance(count, str) and count.startswith("Error:"):
                return f"Combinations: {count}" # "Error: " を含めて表示
            elif isinstance(count, (int, float)):
                return f"Combinations: {count:,}"
            else:
                # 予期せぬ型の場合や計算失敗（エラー文字列以外）
                return f"Combinations: Calculation error or invalid type ({type(count)})"

        with gr.Row(): # reload_button は単独で配置されることが多いのでRowは不要かも
            reload_button = gr.Button('🔄', variant='secondary', elem_id='easy_prompt_selector_reload_button')
            # Gradioの新しいバージョンでは size 引数がある
            # reload_button = gr.Button('🔄', variant='secondary', elem_id='easy_prompt_selector_reload_button', size='sm')


        selection_mode_radio = gr.Radio(
            choices=["round_robin", "random"],
            value=self.selection_mode,
            label="Selection Mode",
            elem_id="easy_prompt_selector_selection_mode_radio"
        )

        combination_count_html = gr.HTML(
            value=_update_combination_count_display(""), # 初期プロンプトは空として計算
            elem_id="easy_prompt_selector_combination_count_html"
        )

        # JavaScriptからプロンプトテキストを受け取るための隠しテキストボックス
        prompt_textbox_input = gr.Textbox(visible=False, elem_id="eps_prompt_textbox_input")

        # --- イベントリスナーの設定 ---
        # 1. 隠しテキストボックスの値が変更されたら、組み合わせ数を更新
        prompt_textbox_input.input( # .input() は入力のたびに発火
            fn=_update_combination_count_display,
            inputs=[prompt_textbox_input],
            outputs=[combination_count_html],
            # 頻繁な更新を避けるために debounce や throttle を検討しても良い
            # debounce=0.5, # 0.5秒入力が止まったら発火
        )

        # 2. リロードボタンがクリックされたときの処理
        def reload_all(selection_mode_value, current_prompt_text):
            # --- タグの再読み込み ---
            try:
                self.tags = load_tags()
            except Exception as e:
                err_msg = f"Error loading tags: {e}"
                print(err_msg)
                # UI にもエラーを表示
                return selection_mode_value, f"Combinations: {err_msg}"

            # --- 追加のセットアップ処理 ---
            try:
                import importlib.util, pathlib
                setup_path = pathlib.Path(__file__).with_name('setup.py')
                spec = importlib.util.spec_from_file_location('eps_setup', setup_path)
                if spec and spec.loader:
                    setup_mod = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(setup_mod)
                    if hasattr(setup_mod, 'write_filename_list') and callable(setup_mod.write_filename_list):
                        setup_mod.write_filename_list()
            except Exception as e:
                err_msg = f"Error calling write_filename_list: {e}"
                print(err_msg)
                return selection_mode_value, f"Combinations: {err_msg}"

            # --- 内部状態のリセット ---
            self.combinations = []
            self.current_combination_index = 0
            self.previous_prompt = None  # プロンプトが変わった扱いにするためキャッシュをクリア
            self.selection_mode = selection_mode_value

            # --- リロード後、現在のプロンプトで組み合わせ数を再計算して表示 ---
            combination_text = _update_combination_count_display(current_prompt_text)
            return selection_mode_value, combination_text

        reload_button.click(
            fn=reload_all,
            inputs=[selection_mode_radio, prompt_textbox_input],
            outputs=[selection_mode_radio, combination_count_html]
        )

        # 3. 選択モードが変更されたときの処理
        def handle_selection_mode_change(mode, current_prompt_text):
            self.selection_mode = mode
            # モード変更時に previous_prompt をリセットして、次の生成時に組み合わせを再生成させる
            self.previous_prompt = None 
            self.combinations = []
            self.current_combination_index = 0
            # モード変更時にも組み合わせ数を表示更新（表示内容は変わらないかもしれないがUIの一貫性のため）
            # combination_text = _update_combination_count_display(current_prompt_text)
            # return mode, combination_text # 組み合わせ数表示も更新する場合
            return mode # モードのみ更新する場合

        selection_mode_radio.change(
            fn=handle_selection_mode_change,
            inputs=[selection_mode_radio, prompt_textbox_input],
            # outputs=[selection_mode_radio, combination_count_html] # 組み合わせ数も更新する場合
            outputs=[selection_mode_radio] # モードのみ更新する場合
        )

        return [reload_button, selection_mode_radio, combination_count_html, prompt_textbox_input]

    def replace_template_round_robin(self, prompt):
        if not '@' in prompt:
            return prompt, []

        parsed_templates = [parse_template(match) for match in re.finditer(r'(@((?P<num>\d+(-\d+)?)\$\$)?(?P<ref>[^>]+?)@)', prompt)]
        
        # プロンプトが変更されたか、組み合わせリストが空の場合に再生成
        if not self.combinations or self.previous_prompt != prompt:
            # calculate_combinations_count でエラーチェックはされているはず
            # ここで再度エラーチェックしても良い
            count_check = calculate_combinations_count(self.tags, prompt)
            if isinstance(count_check, str) and count_check.startswith("Error:"):
                return count_check, [count_check] # エラーメッセージをプロンプトとして返し、情報にも含める

            self.combinations = generate_combinations(self.tags, parsed_templates)
            self.current_combination_index = 0
            self.previous_prompt = prompt # 現在のプロンプトを記録

        if not self.combinations:
            # generate_combinations が空リストを返した場合 (エラーケースを含む可能性)
            # generate_combinations 内でエラーが文字列として要素に含まれる場合がある
            if self.previous_prompt: # プロンプトが設定されていれば、それに対するエラーの可能性
                err_msg_calc = calculate_combinations_count(self.tags, self.previous_prompt)
                if isinstance(err_msg_calc, str) and err_msg_calc.startswith("Error:"):
                    return err_msg_calc, [err_msg_calc]
            return "Error: No combinations generated (check tags or prompt template, or an error occurred during generation).", []


        if self.current_combination_index >= len(self.combinations):
            self.current_combination_index = 0 # インデックスをリセット

        if not self.combinations: # 再度チェック (上のifでreturnするはずだが念のため)
             return "Error: Combinations list is unexpectedly empty after reset.", []

        current_selection = self.combinations[self.current_combination_index]

        # エラーチェック: current_selection の各要素がエラーメッセージを含んでいないか
        errors_in_selection = [item for item in current_selection if isinstance(item, str) and item.startswith("Error:")]
        if errors_in_selection:
            # エラーがある場合、エラーメッセージを結合して表示
            full_error_message = "Error in generated combination: " + ", ".join(errors_in_selection)
            # プロンプト自体もエラーメッセージにするか、元のプロンプトの一部を置換するか選択
            # ここでは、エラーメッセージをプロンプトとして返す
            replaced_prompt = full_error_message
            # p.extra_generation_params にも詳細なエラーを残すと良い
        else:
            replaced_prompt = prompt
            try:
                for i, template_info in enumerate(parsed_templates):
                    # current_selection[i] が存在するかチェック
                    if i < len(current_selection):
                        replacement_value = str(current_selection[i])
                        # template_info['template'] が元のプロンプトに存在するか確認しながら置換
                        if template_info['template'] in replaced_prompt:
                           replaced_prompt = replaced_prompt.replace(template_info['template'], replacement_value, 1)
                        else:
                            # テンプレートが既にない場合（前の置換で消えたなど）、ログを出すなど検討
                            print(f"Warning: Template '{template_info['template']}' not found in prompt for replacement.")
                    else:
                        # 組み合わせの要素数がテンプレート数より少ない場合（エラーケース）
                        error_msg_short = f"Error: Combination data missing for template {i+1} ('{template_info['ref']}')."
                        print(error_msg_short) # ログ出力
                        # このエラーをプロンプトに含めるか検討
                        # replaced_prompt += f" ({error_msg_short})" 
                        break # 以降の置換は不可能
            except IndexError: # current_selection[i] でエラーが発生した場合
                error_msg_index = "Error: Index out of bounds while replacing templates. Combination data might be incomplete."
                print(error_msg_index)
                replaced_prompt = error_msg_index # エラーをプロンプトとして返す
            except Exception as e: # pylint: disable=broad-except
                error_msg_general = f"Error during template replacement: {e}"
                print(error_msg_general)
                replaced_prompt = error_msg_general # エラーをプロンプトとして返す


        # --- 表示用情報の組み立て ---
        if self.combinations:
            # YAML パスを '>' で連結してタイトルとして表示
            yaml_titles = [">".join(template_info['ref']) for template_info in parsed_templates]
            yaml_titles_str = ", ".join(yaml_titles) if yaml_titles else ""
            current_combination_display_info = f"{self.current_combination_index + 1}/{len(self.combinations)} {yaml_titles_str}".strip()
        else:
            current_combination_display_info = "No combinations"

        # プロンプト内容は表示せず、組み立てた情報のみを出力
        if shared.opts.eps_show_current_combination:
            print(f"EasyPromptSelector Round Robin: {current_combination_display_info}")
        
        self.current_combination_index += 1
        return replaced_prompt, [current_combination_display_info]


    def replace_template_tags(self, p):
        # このメソッドは p.all_prompts などを直接変更するため、リストの各要素に対して処理を行う
        
        # p.all_prompts, p.all_negative_prompts など、処理対象のプロンプトリストを取得
        prompt_fields_to_process = []
        if hasattr(p, 'all_prompts'):
            prompt_fields_to_process.append({'list': p.all_prompts, 'raw_name': 'Input Prompt'})
        if hasattr(p, 'all_negative_prompts'):
            prompt_fields_to_process.append({'list': p.all_negative_prompts, 'raw_name': 'Input NegativePrompt'})
        if hasattr(p, 'all_hr_prompts') and getattr(p, 'hr_prompt', None): # Hires fix が有効な場合のみ
             prompt_fields_to_process.append({'list': p.all_hr_prompts, 'raw_name': 'Input Prompt(Hires)'})
        if hasattr(p, 'all_hr_negative_prompts') and getattr(p, 'hr_negative_prompt', None): # Hires fix が有効な場合のみ
             prompt_fields_to_process.append({'list': p.all_hr_negative_prompts, 'raw_name': 'Input NegativePrompt(Hires)'})


        # バッチ処理内の各プロンプトに対して処理
        # バッチサイズ（p.n_iter * p.batch_size に相当する all_prompts の長さ）
        num_images = len(p.all_prompts) if hasattr(p, 'all_prompts') and p.all_prompts else 1

        for i in range(num_images):
            # 各画像生成ごとに独立したランダムシードを使用（randomモードの場合）
            # round-robinモードではこのseedは直接使われないが、一貫性のために設定しても良い
            image_seed = p.all_seeds[i] if hasattr(p, 'all_seeds') and i < len(p.all_seeds) else None


            for field_info in prompt_fields_to_process:
                prompt_list = field_info['list']
                raw_prompt_name = field_info['raw_name']

                if i < len(prompt_list): # インデックス範囲チェック
                    original_prompt_for_ith_image = prompt_list[i]
                    
                    # 組み合わせ数計算 (表示用、最初のプロンプトに対してのみ計算・保存)
                    if i == 0: # バッチの最初の画像に対してのみPNG infoに保存
                        if '@' not in original_prompt_for_ith_image:
                            combination_count = 1
                        else:
                            combination_count = calculate_combinations_count(self.tags, original_prompt_for_ith_image)

                        if isinstance(combination_count, str) and combination_count.startswith("Error:"):
                            # print(f"EasyPromptSelector: Combination Count Error for {raw_prompt_name} - {combination_count.split('Error: ')[1]}")
                            p.extra_generation_params[f"EPS {raw_prompt_name} Combination Count"] = combination_count
                        else:
                            p.extra_generation_params[f"EPS {raw_prompt_name} Combination Count"] = f"{combination_count:,}"
                    
                    # テンプレート置換処理
                    if '@' in original_prompt_for_ith_image:
                        self.save_prompt_to_pnginfo(p, original_prompt_for_ith_image, raw_prompt_name, i) # 元のプロンプトを保存

                        if self.selection_mode == "round_robin":
                            replaced_prompt, combination_info = self.replace_template_round_robin(original_prompt_for_ith_image)
                            if shared.opts.eps_show_current_combination and combination_info and i == 0: # バッチの最初のみ
                                p.extra_generation_params[f"EPS {raw_prompt_name} Selection"] = combination_info[0]
                            prompt_list[i] = replaced_prompt
                        else: # random mode
                            # randomモードでは各プロンプトフィールドごとに独立してランダム置換
                            # image_seed を使うことで、同じ画像に対する各プロンプトフィールドのランダム性が一貫する
                            # （ただし、プロンプトとネガティブプロンプトで同じタグ群を使う場合、同じものが選ばれる可能性）
                            # より独立させたいなら、フィールドごとにも異なるseed要素を加える
                            field_specific_seed = hash((image_seed, raw_prompt_name)) if image_seed is not None else None
                            replaced_prompt = replace_template_random(self.tags, original_prompt_for_ith_image, field_specific_seed)
                            prompt_list[i] = replaced_prompt


    def save_prompt_to_pnginfo(self, p, prompt_text, name_prefix, batch_index):
        if not shared.opts.eps_enable_save_raw_prompt_to_pnginfo:
            return
        # バッチ処理の場合、どの画像に対応するプロンプトかわかるようにキーを工夫する
        # ただし、extra_generation_params は画像ごとではなく、処理全体で一つ。
        # そのため、バッチの最初のプロンプトのみを保存するか、全バッチ分を連結して保存するかなどの工夫が必要。
        # ここでは、バッチの最初の画像(index 0)のプロンプトのみを保存する。
        if batch_index == 0:
            param_name = f"EPS Raw {name_prefix}"
            p.extra_generation_params[param_name] = prompt_text.replace('\n', ' ')


    def process(self, p, *args): # args はスクリプト設定で渡される値
        # is_enabled などの設定をargsから受け取る場合がある
        self.replace_template_tags(p)
