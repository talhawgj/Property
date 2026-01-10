import "react"
const FormField = ({ label, children }: { label: string; children: React.ReactNode }) => (
  <div>
    <label className="text-xs text-muted-foreground tracking-wider mb-1 block">{label}</label>
    {children}
  </div>
)


const InfoField = ({ label, value }: { label: string; value: string | number | null | undefined }) => (
  <div>
    <p className="text-xs text-muted-foreground tracking-wider mb-1">{label}</p>
    <p className="text-sm font-mono">{value ?? "N/A"}</p>
  </div>
)


const SectionHeader = ({ title }: { title: string }) => (
  <h3 className="text-sm font-bold text-foreground mb-3 tracking-wider">{title}</h3>
)


export {FormField,InfoField,SectionHeader};