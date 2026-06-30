import { cn } from "@/lib/utils";

export function Logo({ className, showWord = true }: { className?: string; showWord?: boolean }) {
  return (
    <span className={cn("inline-flex items-center gap-2.5", className)}>
      <span className="relative grid size-8 place-items-center rounded-lg accent-bg text-white shadow-sm">
        <svg viewBox="0 0 24 24" className="h-[18px] w-[18px]" fill="none" aria-hidden>
          <path
            d="M12 2 4 5.5v6c0 4.6 3.2 8.4 8 10.5 4.8-2.1 8-5.9 8-10.5v-6L12 2Z"
            fill="currentColor" opacity="0.2"
          />
          <path
            d="M12 2 4 5.5v6c0 4.6 3.2 8.4 8 10.5 4.8-2.1 8-5.9 8-10.5v-6L12 2Z"
            stroke="currentColor" strokeWidth="1.6" strokeLinejoin="round"
          />
          <path d="m8.5 12 2.4 2.4L15.8 9.5" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      </span>
      {showWord && <span className="text-[17px] font-semibold tracking-tight">Certo</span>}
    </span>
  );
}
