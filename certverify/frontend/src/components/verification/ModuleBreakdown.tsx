import React, { useState } from 'react';
import {
  AlertTriangle,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  Minus,
  XCircle,
} from 'lucide-react';
import { VerificationResult } from '../../types';
import { Badge } from '../ui/badge';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../ui/table';

interface ModuleBreakdownProps {
  results: VerificationResult[];
}

export const ModuleBreakdown: React.FC<ModuleBreakdownProps> = ({ results }) => {
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const toggleRow = (id: string) => {
    setExpandedId(expandedId === id ? null : id);
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'PASS':
        return (
          <Badge variant="success" className="gap-1">
            <CheckCircle2 className="h-3 w-3" /> PASS
          </Badge>
        );
      case 'WARNING':
        return (
          <Badge variant="warning" className="gap-1">
            <AlertTriangle className="h-3 w-3" /> WARNING
          </Badge>
        );
      case 'FAIL':
        return (
          <Badge variant="destructive" className="gap-1">
            <XCircle className="h-3 w-3" /> FAIL
          </Badge>
        );
      case 'SKIPPED':
      default:
        return (
          <Badge variant="secondary" className="gap-1 text-slate-500">
            <Minus className="h-3 w-3" /> SKIPPED
          </Badge>
        );
    }
  };

  return (
    <Card className="shadow-sm border-slate-200">
      <CardHeader className="border-b border-slate-100 pb-4">
        <CardTitle className="text-base font-semibold">Verification Module Breakdown</CardTitle>
        <CardDescription>
          Detailed outcomes from each individual AI and forensic verification engine (click row to inspect JSON)
        </CardDescription>
      </CardHeader>
      <CardContent className="p-0">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-10"></TableHead>
              <TableHead>Analysis Module</TableHead>
              <TableHead>Outcome</TableHead>
              <TableHead>Finding Summary</TableHead>
              <TableHead className="text-right">Confidence</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {results.map((result) => {
              const isExpanded = expandedId === result.id;
              return (
                <React.Fragment key={result.id}>
                  <TableRow
                    onClick={() => toggleRow(result.id)}
                    className="cursor-pointer hover:bg-slate-50 transition-colors"
                  >
                    <TableCell className="text-slate-400">
                      {isExpanded ? (
                        <ChevronDown className="h-4 w-4" />
                      ) : (
                        <ChevronRight className="h-4 w-4" />
                      )}
                    </TableCell>
                    <TableCell className="font-semibold text-slate-900">
                      {result.module_name.replace(/_/g, ' ')}
                    </TableCell>
                    <TableCell>{getStatusBadge(result.status)}</TableCell>
                    <TableCell className="text-xs text-slate-700 max-w-md truncate">
                      {result.finding_summary}
                    </TableCell>
                    <TableCell className="text-right font-mono text-xs text-slate-600">
                      {result.confidence_score !== null && result.confidence_score !== undefined
                        ? `${(result.confidence_score * 100).toFixed(0)}%`
                        : '—'}
                    </TableCell>
                  </TableRow>
                  {isExpanded && (
                    <TableRow className="bg-slate-50/70 border-b border-slate-200">
                      <TableCell colSpan={5} className="p-4">
                        <div className="bg-slate-900 text-slate-200 p-4 rounded-lg font-mono text-xs overflow-x-auto max-h-60">
                          <p className="text-[10px] text-slate-400 uppercase mb-2">Raw Telemetry &amp; Module Details:</p>
                          <pre>{JSON.stringify(result.details, null, 2)}</pre>
                        </div>
                      </TableCell>
                    </TableRow>
                  )}
                </React.Fragment>
              );
            })}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  );
};

