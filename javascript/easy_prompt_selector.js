class EPSElementBuilder {
  // Templates
  static baseButton(text, { size = 'sm', color = 'primary' }) {
    const button = gradioApp().getElementById('txt2img_generate').cloneNode()
    button.id = ''
    button.classList.remove('gr-button-lg', 'gr-button-primary', 'lg', 'primary')
    button.classList.add(
      // gradio 3.16
      `gr-button-${size}`,
      `gr-button-${color}`,
      // gradio 3.22
      size,
      color
    )
    button.textContent = text

    return button
  }

  static tagFields() {
    const fields = document.createElement('div')
    fields.style.display = 'flex'
    fields.style.flexDirection = 'row'
    fields.style.flexWrap = 'wrap'
    fields.style.minWidth = 'min(320px, 100%)'
    fields.style.maxWidth = '100%'
    fields.style.flex = '1 calc(50% - 20px)'
    fields.style.borderWidth = '1px'
    fields.style.borderColor = 'var(--block-border-color,#374151)'
    fields.style.borderRadius = 'var(--block-radius,8px)'
    fields.style.padding = '8px'
    fields.style.height = 'fit-content'

    return fields
  }

  // Elements
  static openButton({ onClick }) {
    const button = EPSElementBuilder.baseButton('🔯タグを選択', { size: 'sm', color: 'secondary' })
    button.classList.add('easy_prompt_selector_button')

    // ボタンの高さ調整: 縦長になるのを防ぐ
    // reloadButton (size='sm') のスタイルに近づけるため、padding と line-height を調整
    button.style.height = 'auto'; // 高さはpaddingに依存させる
    // 一般的な 'sm' ボタンのパディング (値はGradioのバージョンやテーマで微調整が必要な場合があります)
    // 上下のパディングを小さくし、行の高さを標準にすることで、ボタンが縦に伸びるのを抑制します。
    button.style.paddingTop = 'var(--spacing-sm, 4px)';
    button.style.paddingBottom = 'var(--spacing-sm, 4px)';
    // 左右のパディングはgr-button-smクラスに任せるか、必要なら指定
    // button.style.paddingLeft = 'var(--spacing-md, 8px)';
    // button.style.paddingRight = 'var(--spacing-md, 8px)';
    button.style.lineHeight = 'var(--line-sm, 1.5)'; // または 'normal'

    button.addEventListener('click', onClick)

    return button
  }

  static areaContainer(id = undefined) {
    const container = gradioApp().getElementById('txt2img_results').cloneNode()
    container.id = id
    container.style.gap = 0
    container.style.display = 'none'

    return container
  }

  static tagButton({ title, onClick, onRightClick, color = 'primary' }) {
    const button = EPSElementBuilder.baseButton(title, { color })
    button.style.height = '2rem'
    button.style.flexGrow = '0'
    button.style.margin = '2px'

    button.addEventListener('click', onClick)
    button.addEventListener('contextmenu', onRightClick)

    return button
  }

  static dropDown(id, options, { onChange }) {
    const select = document.createElement('select')
    select.id = id

    // gradio 3.16
    select.classList.add('gr-box', 'gr-input')

    // gradio 3.22
    select.style.color = 'var(--body-text-color)'
    select.style.backgroundColor = 'var(--input-background-fill)'
    select.style.borderColor = 'var(--block-border-color)'
    select.style.borderRadius = 'var(--block-radius)'
    select.style.margin = '2px'
    select.addEventListener('change', (event) => { onChange(event.target.value) })

    const none = ['なし']
    none.concat(options).forEach((key) => {
      const option = document.createElement('option')
      option.value = key
      option.textContent = key
      select.appendChild(option)
    })

    return select
  }

  static checkbox(text, { onChange }) {
    const label = document.createElement('label')
    label.style.display = 'flex'
    label.style.alignItems = 'center'

    const checkbox = gradioApp().querySelector('input[type=checkbox]').cloneNode()
    checkbox.checked = false
    checkbox.addEventListener('change', (event) => {
       onChange(event.target.checked)
    })

    const span = document.createElement('span')
    span.style.marginLeft = 'var(--size-2, 8px)'
    span.textContent = text

    label.appendChild(checkbox)
    label.appendChild(span)

    return label
  }
}

class EasyPromptSelector {
  PATH_FILE = 'tmp/easyPromptSelector.txt'
  AREA_ID = 'easy-prompt-selector'
  SELECT_ID = 'easy-prompt-selector-select'
  CONTENT_ID = 'easy-prompt-selector-content'
  TO_NEGATIVE_PROMPT_ID = 'easy-prompt-selector-to-negative-prompt'

  constructor(yaml, gradioApp) {
    this.yaml = yaml
    this.gradioApp = gradioApp
    this.visible = false
    this.toNegative = false
    this.tags = undefined
  }

  async init() {
    this.tags = await this.parseFiles()

    const tagArea = gradioApp().querySelector(`#${this.AREA_ID}`)
    if (tagArea != null) {
      this.visible = false
      this.changeVisibility(tagArea, this.visible)
      tagArea.remove()
    }

    gradioApp()
      .getElementById('txt2img_toprow')
      .after(this.render())
  }

  async readFile(filepath) {
    const response = await fetch(`file=${filepath}?${new Date().getTime()}`);

    return await response.text();
  }

  async parseFiles() {
    const text = await this.readFile(this.PATH_FILE);
    if (text === '') { return {} }

    const paths = text.split(/\r\n|\n/)

    const tags = {}
    for (const path of paths) {
      const filename = path.split('/').pop().split('.').slice(0, -1).join('.')
      const data = await this.readFile(path)
      yaml.loadAll(data, function (doc) {
        tags[filename] = doc
      })
    }

    return tags
  }

  // Render
  render() {
    const row = document.createElement('div')
    row.style.display = 'flex'
    row.style.alignItems = 'center'
    row.style.gap = '10px'

    const dropDown = this.renderDropdown()
    dropDown.style.flex = '1'
    dropDown.style.minWidth = '1'
    row.appendChild(dropDown)

    const settings = document.createElement('div')
    const checkbox = EPSElementBuilder.checkbox('ネガティブプロンプトに入力', {
      onChange: (checked) => { this.toNegative = checked }
    })
    settings.style.flex = '1'
    settings.appendChild(checkbox)

    row.appendChild(settings)

    const container = EPSElementBuilder.areaContainer(this.AREA_ID)

    container.appendChild(row)
    container.appendChild(this.renderContent())

    return container
  }

  renderDropdown() {
    const dropDown = EPSElementBuilder.dropDown(
      this.SELECT_ID,
      Object.keys(this.tags), {
        onChange: (selected) => {
          const content = gradioApp().getElementById(this.CONTENT_ID)
          Array.from(content.childNodes).forEach((node) => {
            const visible = node.id === `easy-prompt-selector-container-${selected}`
            this.changeVisibility(node, visible)
          })
        }
      }
    )

    return dropDown
  }

  renderContent() {
    const content = document.createElement('div')
    content.id = this.CONTENT_ID

    Object.keys(this.tags).forEach((key) => {
      const values = this.tags[key]

      const fields = EPSElementBuilder.tagFields()
      fields.id = `easy-prompt-selector-container-${key}`
      fields.style.display = 'none'
      fields.style.flexDirection = 'row'
      fields.style.marginTop = '10px'

      this.renderTagButtons(values, key).forEach((group) => {
        fields.appendChild(group)
      })

      content.appendChild(fields)
    })

    return content
  }

  renderTagButtons(tags, prefix = '') {
    if (Array.isArray(tags)) {
      return tags.map((tag) => this.renderTagButton(tag, tag, 'secondary'))
    } else {
      return Object.keys(tags).map((key) => {
        const values = tags[key]
        const randomKey = `${prefix}:${key}`

        if (typeof values === 'string') { return this.renderTagButton(key, values, 'secondary') }

        const fields = EPSElementBuilder.tagFields()
        fields.style.flexDirection = 'column'

        fields.append(this.renderTagButton(key, `@${randomKey}@`))

        const buttons = EPSElementBuilder.tagFields()
        buttons.id = 'buttons'
        fields.append(buttons)
        this.renderTagButtons(values, randomKey).forEach((button) => {
          buttons.appendChild(button)
        })

        return fields
      })
    }
  }

  renderTagButton(title, value, color = 'primary') {
    return EPSElementBuilder.tagButton({
      title,
      onClick: (e) => {
        e.preventDefault();

        this.addTag(value, this.toNegative || e.metaKey || e.ctrlKey)
      },
      onRightClick: (e) => {
        e.preventDefault();

        this.removeTag(value, this.toNegative || e.metaKey || e.ctrlKey)
      },
      color
    })
  }

  // Util
  changeVisibility(node, visible) {
    node.style.display = visible ? 'flex' : 'none'
  }

  // EasyPromptSelector クラス内の addTag メソッドを以下に置き換えます。
  addTag(tag, toNegative = false) {
    const id = toNegative ? 'txt2img_neg_prompt' : 'txt2img_prompt';
    const textarea = gradioApp().getElementById(id).querySelector('textarea');

    if (!textarea) {
      console.error(`Textarea with id ${id} not found.`);
      return;
    }

    const currentText = textarea.value;
    const selectionStart = textarea.selectionStart; // 選択範囲の開始位置またはカーソル位置
    const selectionEnd = textarea.selectionEnd;     // 選択範囲の終了位置またはカーソル位置

    // 挿入するタグの前後にスペースやカンマを自動で付与するかどうかを決定する
    // ここでは、元のロジックに近い形で、ある程度の自動調整を試みます。
    // ただし、カーソル位置挿入では完璧な自動調整は難しいため、シンプルな挿入を基本とします。
    // ユーザーの利便性を考え、タグの前後にスペースがない場合、半角スペースを一つ入れることを基本とする。
    // カンマはユーザーが意識して入力することを推奨。

    let tagToInsert = tag;
    let finalCursorPos = selectionStart + tagToInsert.length;

    // 選択範囲の前の文字
    const charBefore = selectionStart > 0 ? currentText[selectionStart - 1] : null;
    // 選択範囲の後の文字
    const charAfter = selectionEnd < currentText.length ? currentText[selectionEnd] : null;

    // 前にスペースが必要か (テキストの先頭でなく、かつ直前がスペースやカンマでない場合)
    let needsSpaceBefore = selectionStart > 0 && charBefore !== ' ' && charBefore !== ',';
    // 後にスペースが必要か (テキストの末尾でなく、かつ直後がスペースやカンマでない場合)
    let needsSpaceAfter = selectionEnd < currentText.length && charAfter !== ' ' && charAfter !== ',';


    // 既存のテキストが空、またはカーソルがテキストの先頭かつ末尾（つまり空で挿入）の場合は、タグのみ
    if (currentText.trim() === '' && selectionStart === 0 && selectionEnd === currentText.length) {
        // テキストエリアが完全に空で、そこに挿入する場合
        tagToInsert = tag;
    } else {
        // ある程度賢いスペースの挿入を試みる
        // ただし、複雑になりすぎないように、基本は「タグの前後が文字ならスペースを入れる」程度に留める
        let prefix = "";
        let suffix = "";

        if (needsSpaceBefore) {
            prefix = ", ";
        }
        if (needsSpaceAfter && tagToInsert.trim() !== "") { // タグ自体が空白文字のみの場合は後ろにスペース不要
            suffix = ", ";
        }
        
        // もしカーソルが単語の途中にあれば、スペースは不要な場合が多い
        // 例: wo|rd に tag を挿入 -> wotagrd (スペースなし)
        // この判定は複雑なので、今回はシンプルに「タグの前後に非空白文字があればスペースを付与する」方針でいく
        // より洗練されたロジックが必要な場合は、さらに詳細な条件分岐が必要

        // 既存のロジック（末尾追加時のカンマ付与など）をカーソル位置挿入にそのまま適用するのは難しい。
        // ここでは、タグの前にスペース、タグの後にスペースを基本とする。
        // カンマはユーザーが手動で入れることを期待する。

        if (selectionStart > 0 && currentText[selectionStart-1] !== ' ' && currentText[selectionStart-1] !== ',') {
            tagToInsert = prefix + tagToInsert;
        }
        // タグの後ろのスペースは、タグ自体がスペースで終わっていない場合、かつ、カーソルの後ろがスペースやカンマでない場合
        if (tag.trim() !== "" && !tag.endsWith(' ') && selectionEnd < currentText.length && currentText[selectionEnd] !== ' ' && currentText[selectionEnd] !== ',') {
            tagToInsert = tagToInsert + suffix;
        } else if (tag.trim() !== "" && !tag.endsWith(' ') && selectionEnd === currentText.length) {
            // カーソルが末尾の場合は、後ろにスペースを追加しても良いことが多い
            tagToInsert = tagToInsert + suffix;
        }


        // もし、挿入するタグが既に前後に適切なスペースやカンマを含んでいる場合は、
        // 上記の自動スペース付与は過剰になる可能性がある。
        // そのため、タグの内容に応じて調整が必要になる場合がある。
        // ここでは、汎用的なケースとして、上記のようなスペース処理を行う。
    }


    // 選択範囲を置き換えるか、カーソル位置に挿入
    textarea.value = currentText.substring(0, selectionStart) +
                     tagToInsert +
                     currentText.substring(selectionEnd);

    // 挿入後、カーソルを挿入されたタグの末尾に移動
    finalCursorPos = selectionStart + tagToInsert.length;
    textarea.selectionStart = finalCursorPos;
    textarea.selectionEnd = finalCursorPos;

    updateInput(textarea); // Gradioに更新を通知
    textarea.focus();      // テキストエリアにフォーカスを戻す（操作性を良くするため）
  }

  removeTag(tag, toNegative = false) {
    const id = toNegative ? 'txt2img_neg_prompt' : 'txt2img_prompt'
    const textarea = gradioApp().getElementById(id).querySelector('textarea')

    if (textarea.value.trimStart().startsWith(tag)) {
      const matched = textarea.value.match(new RegExp(`${tag.replace(/[-\/\\^$*+?.()|\[\]{}]/g, '\\$&') },*`))
      textarea.value = textarea.value.replace(matched[0], '').trimStart()
    } else {
      textarea.value = textarea.value.replace(`, ${tag}`, '')
    }

    updateInput(textarea)
  }
}

onUiLoaded(async () => {
  yaml = window.jsyaml;
  const easyPromptSelector = new EasyPromptSelector(yaml, gradioApp());

  const openTagSelectorButton = EPSElementBuilder.openButton({
    onClick: () => {
      const tagArea = gradioApp().querySelector(`#${easyPromptSelector.AREA_ID}`);
      easyPromptSelector.changeVisibility(tagArea, easyPromptSelector.visible = !easyPromptSelector.visible);
    }
  });

  const reloadButton = gradioApp().getElementById('easy_prompt_selector_reload_button');
  const selectionModeRadio = gradioApp().getElementById('easy_prompt_selector_selection_mode_radio');
  const combinationCountHTML = gradioApp().getElementById('easy_prompt_selector_combination_count_html');
  const promptInputGradioElement = gradioApp().getElementById('eps_prompt_textbox_input'); // 隠しテキストボックスを取得

  if (reloadButton) {
    reloadButton.addEventListener('click', async () => {
      // ★★★ デバッグ用: リロードボタンクリック時の隠しテキストボックスの値をログに出力 ★★★
      if (promptInputGradioElement) {
          console.log("EPS_JS_DEBUG: Reload button clicked. Initial value of eps_prompt_textbox_input:", promptInputGradioElement.value);
      } else {
          console.error("EPS_JS_DEBUG: eps_prompt_textbox_input element not found at click time!");
      }
      // ★★★ デバッグここまで ★★★

      // メインのプロンプトテキストエリアから最新の値を取得して隠しテキストボックスに設定する
      // この処理は Python 側で Gradio の inputs を介して値が取得される前に行う必要がある。
      // Gradio の click イベントの inputs は、イベント発火時のコンポーネントの値を参照するため、
      // この JavaScript の click リスナー内で値を更新しても、Python 側の click ハンドラが
      // 古い値を見てしまう可能性がある。
      // より確実なのは、Python 側の reload_all_action 関数が呼び出される *直前* に
      // この値がセットされていること。
      // Gradio の仕組み上、JS のイベントリスナーと Python の Gradio イベントハンドラは
      // 実行順序が必ずしも保証されない場合がある。

      // 一旦、easyPromptSelector.init() の前にプロンプト更新を試みる
      const mainPromptTextarea = gradioApp().querySelector("#txt2img_prompt textarea") || gradioApp().querySelector("#img2img_prompt textarea");
      if (mainPromptTextarea && promptInputGradioElement) {
          promptInputGradioElement.value = mainPromptTextarea.value;
          // input イベントを発行して Gradio 側にも変更を通知
          // これが Python 側の .input() リスナーをトリガーし、
          // さらに Gradio が管理するコンポーネントの状態を更新するはず。
          promptInputGradioElement.dispatchEvent(new Event('input', { bubbles: true, cancelable: true }));
          console.log("EPS_JS_DEBUG: Updated eps_prompt_textbox_input with value from main textarea:", promptInputGradioElement.value);
      } else {
          if (!mainPromptTextarea) console.error("EPS_JS_DEBUG: Main prompt textarea not found for update!");
          if (!promptInputGradioElement) console.error("EPS_JS_DEBUG: eps_prompt_textbox_input not found for update!");
      }
      
      // easyPromptSelector.init() はタグファイルの再読み込みなどを行う
      // プロンプトテキストの更新とは直接関係ないが、リロード処理の一部
      await easyPromptSelector.init(); 
      
      // 注意: この JavaScript の click リスナーが完了した後、Gradio のイベントキューを介して
      // Python 側の reload_button.click(...) に登録された関数が呼び出される。
      // その際、inputs=[..., prompt_textbox_input] で参照される値は、
      // 上記の dispatchEvent('input') によって Gradio 側で更新された後の値になることを期待する。
    });
  } else {
    console.error("EasyPromptSelector: Reload button (easy_prompt_selector_reload_button) not found!");
  }


  const txt2imgActionColumn = gradioApp().getElementById('txt2img_actions_column');
  
  const mainUiContainer = document.createElement('div');
  mainUiContainer.classList.add('easy_prompt_selector_main_ui_container');
  mainUiContainer.style.display = 'flex';
  mainUiContainer.style.flexDirection = 'column';
  mainUiContainer.style.gap = 'var(--spacing-md, 8px)';

  const row1 = document.createElement('div');
  row1.style.display = 'flex';
  row1.style.alignItems = 'center';
  row1.style.gap = 'var(--spacing-md, 8px)';

  row1.appendChild(openTagSelectorButton);
  if (reloadButton) { // reloadButton が存在する場合のみ追加
    row1.appendChild(reloadButton);
  }
  
  mainUiContainer.appendChild(row1);

  if (selectionModeRadio) {
    mainUiContainer.appendChild(selectionModeRadio);
  } else {
    console.warn("EasyPromptSelector: selectionModeRadio element not found.");
  }

  if (combinationCountHTML) {
    mainUiContainer.appendChild(combinationCountHTML);
  } else {
    console.warn("EasyPromptSelector: combinationCountHTML element not found.");
  }
  
  if (txt2imgActionColumn) {
    txt2imgActionColumn.appendChild(mainUiContainer);
  } else {
    console.error("EasyPromptSelector: txt2img_actions_column not found! UI cannot be appended.");
  }
  

  await easyPromptSelector.init(); // 初期ロード

  // メインプロンプトエリアの変更を監視し、隠しテキストボックスに値を同期する
  const mainPromptTextareaForSync = gradioApp().querySelector("#txt2img_prompt textarea") || gradioApp().querySelector("#img2img_prompt textarea");
  if (mainPromptTextareaForSync && promptInputGradioElement) {
      mainPromptTextareaForSync.addEventListener('input', () => {
          promptInputGradioElement.value = mainPromptTextareaForSync.value;
          // input イベントを発行して Gradio 側 (Python の .input() リスナー) にも変更を通知
          promptInputGradioElement.dispatchEvent(new Event('input', { bubbles: true, cancelable: true }));
          
          // combinationCountHTML の表示を "Calculating..." に戻す処理はここでも良いが、
          // Python側の .input() リスナーがHTMLを更新するので、二重管理になる可能性。
          // JavaScript側で直接 "Calculating..." にするなら、Python側でのHTML更新を調整する必要がある。
          // if (combinationCountHTML) {
          //   combinationCountHTML.innerHTML = "Combinations: Calculating...";
          // }
      });
      // 初期ロード時にも一度値を同期しておく
      promptInputGradioElement.value = mainPromptTextareaForSync.value;
      promptInputGradioElement.dispatchEvent(new Event('input', { bubbles: true, cancelable: true }));

  } else {
      if (!mainPromptTextareaForSync) console.error("EPS_JS_DEBUG: Main prompt textarea not found for sync event listener!");
      if (!promptInputGradioElement) console.error("EPS_JS_DEBUG: eps_prompt_textbox_input not found for sync event listener!");
  }
});
