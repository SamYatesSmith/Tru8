"use client";

import { useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
  DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { Checkbox } from "@/components/ui/checkbox";
import { useToast } from "@/hooks/use-toast";
import { FileDown, FileJson, FileText, FilePlus } from "lucide-react";
import { ExportService } from "@/lib/export-utils";
import type { Check } from "@shared/types";

interface ExportModalProps {
  check: Check;
  children?: React.ReactNode;
}

export function ExportModal({ check, children }: ExportModalProps) {
  const { toast } = useToast();
  const [format, setFormat] = useState<'pdf' | 'json' | 'markdown'>('pdf');
  const [includeEvidence, setIncludeEvidence] = useState(true);
  const [includeMetadata, setIncludeMetadata] = useState(true);
  const [isExporting, setIsExporting] = useState(false);

  const handleExport = async () => {
    setIsExporting(true);
    
    try {
      await ExportService.exportCheck(check, {
        format,
        includeEvidence,
        includeMetadata,
      });
      
      toast({
        title: "Export successful",
        description: `Your report has been exported as ${format.toUpperCase()}.`,
      });
    } catch (error) {
      toast({
        title: "Export failed",
        description: "There was an error exporting your report. Please try again.",
        variant: "destructive",
      });
    } finally {
      setIsExporting(false);
    }
  };

  const formatIcons = {
    pdf: <FileText className="h-4 w-4" />,
    json: <FileJson className="h-4 w-4" />,
    markdown: <FileDown className="h-4 w-4" />,
  };

  const formatDescriptions = {
    pdf: "Professional report with formatting, ideal for sharing and printing",
    json: "Structured data format for developers and data analysis",
    markdown: "Plain text with formatting, perfect for documentation",
  };

  return (
    <Dialog>
      <DialogTrigger asChild>
        {children || (
          <Button variant="outline">
            <FilePlus className="h-4 w-4 mr-2" />
            Export Report
          </Button>
        )}
      </DialogTrigger>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Export Fact-Check Report</DialogTitle>
          <DialogDescription>
            Choose your export format and options for the fact-check report.
          </DialogDescription>
        </DialogHeader>
        
        <div className="space-y-6 py-4">
          {/* Format Selection */}
          <div className="space-y-3">
            <Label>Export Format</Label>
            <RadioGroup value={format} onValueChange={(v: string) => setFormat(v as 'pdf' | 'json' | 'markdown')}>
              {(['pdf', 'json', 'markdown'] as const).map((fmt) => (
                <div key={fmt} className="flex items-start space-x-3 space-y-0">
                  <RadioGroupItem value={fmt} id={fmt} className="mt-1" />
                  <label
                    htmlFor={fmt}
                    className="flex-1 cursor-pointer space-y-1"
                  >
                    <div className="flex items-center gap-2">
                      {formatIcons[fmt]}
                      <span className="font-medium">{fmt.toUpperCase()}</span>
                    </div>
                    <p className="text-sm text-muted-foreground">
                      {formatDescriptions[fmt]}
                    </p>
                  </label>
                </div>
              ))}
            </RadioGroup>
          </div>

          {/* Options */}
          <div className="space-y-3">
            <Label>Include in Export</Label>
            <div className="space-y-3">
              <div className="flex items-center space-x-2">
                <Checkbox
                  id="evidence"
                  checked={includeEvidence}
                  onCheckedChange={(checked: boolean) => setIncludeEvidence(!!checked)}
                />
                <label
                  htmlFor="evidence"
                  className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70 cursor-pointer"
                >
                  Evidence and sources
                </label>
              </div>
              <div className="flex items-center space-x-2">
                <Checkbox
                  id="metadata"
                  checked={includeMetadata}
                  onCheckedChange={(checked: boolean) => setIncludeMetadata(!!checked)}
                />
                <label
                  htmlFor="metadata"
                  className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70 cursor-pointer"
                >
                  Check metadata (date, processing time, etc.)
                </label>
              </div>
            </div>
          </div>

          {/* Summary */}
          <div className="rounded-lg bg-gray-50 p-3 space-y-1">
            <p className="text-sm font-medium">Export Summary</p>
            <p className="text-xs text-muted-foreground">
              {check.claims?.length || 0} claims will be exported
              {includeEvidence && ` with ${check.claims?.reduce((acc, c) => acc + (c.evidence?.length || 0), 0) || 0} evidence sources`}
            </p>
          </div>
        </div>

        <DialogFooter className="gap-2">
          <DialogTrigger asChild>
            <Button variant="outline">Cancel</Button>
          </DialogTrigger>
          <Button 
            onClick={handleExport} 
            disabled={isExporting}
            className="btn-primary"
          >
            {isExporting ? "Exporting..." : "Export"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}