/** Who built and runs the portal. Rendered on the login page and in the sidebar footer, so
 *  it is visible both before and after sign-in. Kept as one component rather than two copies
 *  of the string so the wording cannot drift between the two places. */
export const ATTRIBUTION = "Developed & maintained by AITEC & CSD Society, IT Dept., Govt. of Assam";

export function Attribution({ className = "", style }: {
  className?: string;
  style?: React.CSSProperties;
}) {
  return (
    <div className={`text-xs leading-snug ${className}`} style={style}>
      {ATTRIBUTION}
    </div>
  );
}
