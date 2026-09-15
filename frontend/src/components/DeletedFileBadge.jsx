import { Check, Trash2 } from "lucide-react";

export default function DeletedFileBadge({ isHead }) {
  return isHead ? (
    <span className="status-badge badge--head"><Check size={13} /> HEAD</span>
  ) : (
    <span className="status-badge badge--deleted"><Trash2 size={13} /> DELETED</span>
  );
}
