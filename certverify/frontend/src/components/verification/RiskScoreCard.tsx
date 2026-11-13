import React, { useState } from 'react';
import { ChevronDown, ChevronUp, ShieldAlert, ShieldCheck, ShieldQuestion } from 'lucide-react';
import { RiskAssessment } from '../../types';
import { Badge } from '../ui/badge';
import { Card, CardContent } from '../ui/card';

interface RiskScoreCardProps {
  assessment: RiskAssessment;
}

export const RiskScoreCard: React.FC<RiskScoreCardProps> = ({ assessment }) => {
  const [showReasoning, setShowReasoning] = useState(true);
  const { risk_score, risk_level, final_verdict, reasoning } = assessment;

  // Arc calculation: circumference = 2 * PI * r
  const radius = 80;
  const stroke = 12;
  const normalizedRadius = radius - stroke * 2;
  const circumference = normalizedRadius * 2 * Math.PI;
  const strokeDashoffset = circumference - (risk_score / 100) * circumference;

  const getScoreColor = (score: number) => {
    if (score <= 30) return '#27ae60'; // Green
    if (score <= 60) return '#f39c12'; // Yellow / Amber
    return '#e74c3c'; // Red
  };

  const getVerdictStyle = () => {
    switch (final_verdict) {
      case 'VERIFIED':
        return {
          banner: 'bg-emerald-50 border border-emerald-500 text-emerald-900',
          badge: 'success' as const,
          icon: ShieldCheck,
          text: 'VERIFIED AUTHENTIC',
        };
      case 'SUSPICIOUS':
        return {
          banner: 'bg-red-50 border border-red-500 text-red-900',
          badge: 'destructive' as const,
          icon: ShieldAlert,
          text: 'POTENTIAL FORGERY / SUSPICIOUS',
        };
      case 'UNABLE_TO_VERIFY':
      default:
        return {
          banner: 'bg-slate-100 border border-slate-400 text-slate-800',
          badge: 'secondary' as const,
          icon: ShieldQuestion,
          text: 'INSUFFICIENT DATA TO VERIFY',
        };
    }
  };

  const verdictConfig = getVerdictStyle();
  const VerdictIcon = verdictConfig.icon;

  return (
    <Card className="shadow-sm border-slate-200">
      <CardContent className="p-6">
        <div className="flex flex-col md:flex-row items-center gap-8 justify-between">
          {/* Gauge meter */}
          <div className="flex flex-col items-center">
            <div className="relative w-[200px] h-[200px] flex items-center justify-center">
              <svg height="200" width="200" className="transform -rotate-90">
                <circle
                  stroke="#f1f5f9"
                  fill="transparent"
                  strokeWidth={stroke}
                  r={normalizedRadius}
                  cx="100"
                  cy="100"
                />
                <circle
                  stroke={getScoreColor(risk_score)}
                  fill="transparent"
                  strokeWidth={stroke}
                  strokeDasharray={`${circumference} ${circumference}`}
                  style={{ strokeDashoffset, transition: 'stroke-dashoffset 0.8s ease' }}
                  strokeLinecap="round"
                  r={normalizedRadius}
                  cx="100"
                  cy="100"
                />
              </svg>
              <div className="absolute inset-0 flex flex-col items-center justify-center text-center">
                <span className="text-4xl font-extrabold text-slate-900 tracking-tight">
                  {risk_score}
                </span>
                <span className="text-xs uppercase font-semibold text-slate-400">/ 100 Risk</span>
              </div>
            </div>
            <div className="mt-1">
              <Badge variant={verdictConfig.badge}>
                {risk_level} RISK LEVEL
              </Badge>
            </div>
          </div>

          {/* Verdict details and description */}
          <div className="flex-1 w-full space-y-4">
            <div className={`p-4 rounded-xl flex items-center gap-3 ${verdictConfig.banner}`}>
              <VerdictIcon className="h-6 w-6 shrink-0" />
              <div>
                <span className="text-xs uppercase font-bold tracking-wider block opacity-75">
                  Automated Audit Determination
                </span>
                <span className="text-base font-extrabold tracking-tight">
                  {verdictConfig.text}
                </span>
              </div>
            </div>

            <div className="bg-slate-50 border border-slate-200 rounded-lg p-4">
              <button
                type="button"
                onClick={() => setShowReasoning(!showReasoning)}
                className="w-full flex items-center justify-between text-xs font-semibold text-slate-700 hover:text-slate-900"
              >
                <span>AI FORENSIC REASONING &amp; SYNTHESIS</span>
                {showReasoning ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
              </button>
              {showReasoning && (
                <p className="text-xs text-slate-600 mt-2 leading-relaxed whitespace-pre-line border-t border-slate-200 pt-2">
                  {reasoning}
                </p>
              )}
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
};

