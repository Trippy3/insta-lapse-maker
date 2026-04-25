interface PathFieldProps {
  value: string | null | undefined;
  placeholder: string;
  onBrowse: () => void;
  onClear?: () => void;
  browseLabel?: string;
}

/**
 * 絶対パス表示 + ブラウズボタン。`<input type="text">` の置き換えとして使う。
 * ユーザーが直接パスを手入力することはできない (readonly)。
 */
export function PathField({
  value,
  placeholder,
  onBrowse,
  onClear,
  browseLabel = "選択...",
}: PathFieldProps) {
  return (
    <div className="path-field" title={value ?? placeholder}>
      {value ? (
        <span className="path-value">{value}</span>
      ) : (
        <span className="path-placeholder">{placeholder}</span>
      )}
      <button onClick={onBrowse}>{browseLabel}</button>
      {onClear && value && (
        <button onClick={onClear} title="クリア">
          ×
        </button>
      )}
    </div>
  );
}
