import React, { useState, useEffect } from 'react';
import {
  Check,
  CheckCircle2,
  Code2,
  Copy,
  Key,
  Loader2,
  Plus,
  Radio,
  Send,
  Trash2,
  Webhook,
} from 'lucide-react';
import {
  createApiKeyApi,
  getWebhookConfigApi,
  listApiKeysApi,
  revokeApiKeyApi,
  testWebhookApi,
  updateWebhookConfigApi,
  ApiKeyCreatedResponse,
  ApiKeyItem,
} from '../api/developer';
import { Button } from '../components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Badge } from '../components/ui/badge';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../components/ui/table';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';

export const DeveloperPage: React.FC = () => {
  const [apiKeys, setApiKeys] = useState<ApiKeyItem[]>([]);
  const [loadingKeys, setLoadingKeys] = useState(false);
  const [newKeyName, setNewKeyName] = useState('');
  const [showKeyModal, setShowKeyModal] = useState(false);
  const [createdKeyData, setCreatedKeyData] = useState<ApiKeyCreatedResponse | null>(null);
  const [copiedKey, setCopiedKey] = useState(false);

  // Webhook state
  const [webhookUrl, setWebhookUrl] = useState('');
  const [webhookSecret, setWebhookSecret] = useState('');
  const [savingWebhook, setSavingWebhook] = useState(false);
  const [testingWebhook, setTestingWebhook] = useState(false);
  const [testResult, setTestResult] = useState<string | null>(null);

  // Snippets tab
  const [snippetLang, setSnippetLang] = useState<'curl' | 'python' | 'node'>('curl');
  const [activeTab, setActiveTab] = useState('keys');

  const loadData = async () => {
    setLoadingKeys(true);
    try {
      const keys = await listApiKeysApi();
      setApiKeys(keys);
      const wh = await getWebhookConfigApi();
      if (wh) {
        setWebhookUrl(wh.url);
        setWebhookSecret(wh.secret);
      }
    } catch (err) {
      // ignore
    } finally {
      setLoadingKeys(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleCreateKey = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newKeyName.trim()) return;

    try {
      const res = await createApiKeyApi(newKeyName.trim());
      setCreatedKeyData(res);
      setNewKeyName('');
      loadData();
    } catch (err) {
      alert('Error creating API key');
    }
  };

  const handleRevokeKey = async (keyId: string) => {
    if (!confirm('Are you sure you want to revoke this API key? External systems using it will lose access immediately.')) return;
    try {
      await revokeApiKeyApi(keyId);
      loadData();
    } catch (err) {
      alert('Error revoking API key');
    }
  };

  const handleCopy = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedKey(true);
    setTimeout(() => setCopiedKey(false), 2000);
  };

  const handleSaveWebhook = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!webhookUrl.trim()) return;

    setSavingWebhook(true);
    try {
      await updateWebhookConfigApi(webhookUrl.trim(), webhookSecret.trim() || undefined);
      alert('Webhook endpoint saved successfully!');
    } catch (err) {
      alert('Error saving webhook configuration');
    } finally {
      setSavingWebhook(false);
    }
  };

  const handleTestWebhook = async () => {
    setTestingWebhook(true);
    setTestResult(null);
    try {
      const res = await testWebhookApi();
      setTestResult(res.message);
    } catch (err: any) {
      setTestResult('Failed to deliver test ping event. Verify your endpoint URL.');
    } finally {
      setTestingWebhook(false);
    }
  };

  return (
    <div className="space-y-8 max-w-7xl mx-auto">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold tracking-tight text-slate-900 flex items-center gap-2">
          <Code2 className="h-8 w-8 text-blue-600" />
          Developer & B2B Integration Suite
        </h1>
        <p className="text-slate-500 mt-1">
          Integrate CertVerify AI verification directly into your EdTech platforms, ATS, or HRMS applications via REST APIs and Webhooks.
        </p>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-6">
        <TabsList className="bg-slate-100 p-1 border">
          <TabsTrigger value="keys" className="flex items-center gap-2">
            <Key className="h-4 w-4" />
            API Keys
          </TabsTrigger>
          <TabsTrigger value="webhooks" className="flex items-center gap-2">
            <Webhook className="h-4 w-4" />
            Webhooks
          </TabsTrigger>
          <TabsTrigger value="quickstart" className="flex items-center gap-2">
            <Radio className="h-4 w-4" />
            API Reference & Code
          </TabsTrigger>
        </TabsList>

        {/* TAB 1: API KEYS */}
        <TabsContent value="keys" className="space-y-6">
          <Card className="border-slate-200 shadow-sm">
            <CardHeader className="flex flex-row items-center justify-between pb-4">
              <div>
                <CardTitle className="text-lg">Production API Keys</CardTitle>
                <CardDescription>
                  API keys authenticate programmatic requests to CertVerify AI endpoints. Pass via the{' '}
                  <code className="text-xs bg-slate-100 px-1 py-0.5 rounded text-blue-600">X-API-Key</code> HTTP header.
                </CardDescription>
              </div>
              <Button
                onClick={() => {
                  setCreatedKeyData(null);
                  setShowKeyModal(true);
                }}
                className="flex items-center gap-1.5 bg-blue-600 hover:bg-blue-700"
              >
                <Plus className="h-4 w-4" />
                Generate New Key
              </Button>
            </CardHeader>
            <CardContent className="p-0">
              <Table>
                <TableHeader>
                  <TableRow className="bg-slate-50/70">
                    <TableHead>Key Label</TableHead>
                    <TableHead>Key Prefix</TableHead>
                    <TableHead>Rate Limit</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Last Used</TableHead>
                    <TableHead>Created</TableHead>
                    <TableHead className="text-right">Action</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {apiKeys.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={7} className="text-center py-8 text-slate-400">
                        {loadingKeys ? 'Loading API keys...' : 'No API keys generated yet. Click Generate New Key to get started.'}
                      </TableCell>
                    </TableRow>
                  ) : (
                    apiKeys.map((k) => (
                      <TableRow key={k.id} className="hover:bg-slate-50/50">
                        <TableCell className="font-medium text-slate-900">{k.name}</TableCell>
                        <TableCell>
                          <code className="text-xs bg-slate-100 px-1.5 py-0.5 rounded font-mono text-slate-700">
                            {k.key_prefix}••••••••
                          </code>
                        </TableCell>
                        <TableCell className="text-xs text-slate-600">{k.rate_limit_per_minute} req/min</TableCell>
                        <TableCell>
                          {k.is_active ? (
                            <Badge className="bg-emerald-100 text-emerald-800 border-none">Active</Badge>
                          ) : (
                            <Badge variant="outline" className="text-slate-400">
                              Revoked
                            </Badge>
                          )}
                        </TableCell>
                        <TableCell className="text-xs text-slate-500">
                          {k.last_used_at ? new Date(k.last_used_at).toLocaleDateString() : 'Never'}
                        </TableCell>
                        <TableCell className="text-xs text-slate-500">
                          {new Date(k.created_at).toLocaleDateString()}
                        </TableCell>
                        <TableCell className="text-right">
                          {k.is_active && (
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => handleRevokeKey(k.id)}
                              className="text-rose-600 hover:text-rose-800 hover:bg-rose-50"
                            >
                              <Trash2 className="h-4 w-4" />
                            </Button>
                          )}
                        </TableCell>
                      </TableRow>
                    ))
                  )}
                </TableBody>
              </Table>
            </CardContent>
          </Card>

          {/* Modal / Banner for newly created key */}
          {createdKeyData && (
            <div className="p-4 bg-emerald-50 border border-emerald-300 rounded-xl space-y-3 animate-fadeIn">
              <div className="flex items-center gap-2 text-emerald-800 font-semibold text-sm">
                <CheckCircle2 className="h-5 w-5 text-emerald-600" />
                API Key Generated Successfully: {createdKeyData.name}
              </div>
              <p className="text-xs text-emerald-700">
                Please copy this key now. For security reasons, it cannot be displayed again.
              </p>
              <div className="flex items-center gap-2">
                <Input
                  readOnly
                  value={createdKeyData.raw_key}
                  className="font-mono text-xs bg-white border-emerald-300 text-slate-800 select-all"
                />
                <Button
                  size="sm"
                  onClick={() => handleCopy(createdKeyData.raw_key)}
                  className="bg-emerald-600 hover:bg-emerald-700 text-white flex items-center gap-1.5"
                >
                  {copiedKey ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
                  {copiedKey ? 'Copied' : 'Copy Key'}
                </Button>
              </div>
            </div>
          )}

          {/* Create Key Form Dialog */}
          {showKeyModal && !createdKeyData && (
            <Card className="border-blue-300 bg-blue-50/20 shadow-md">
              <CardHeader>
                <CardTitle className="text-base">Generate New API Key</CardTitle>
                <CardDescription>Enter a descriptor for your backend or microservice.</CardDescription>
              </CardHeader>
              <CardContent>
                <form onSubmit={handleCreateKey} className="flex flex-col sm:flex-row gap-3">
                  <Input
                    placeholder="e.g. Workday ATS Integration, Staging Service"
                    value={newKeyName}
                    onChange={(e) => setNewKeyName(e.target.value)}
                    className="flex-1"
                  />
                  <div className="flex items-center gap-2">
                    <Button type="submit" className="bg-blue-600 hover:bg-blue-700">
                      Create Key
                    </Button>
                    <Button variant="ghost" type="button" onClick={() => setShowKeyModal(false)}>
                      Cancel
                    </Button>
                  </div>
                </form>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        {/* TAB 2: WEBHOOKS */}
        <TabsContent value="webhooks" className="space-y-6">
          <Card className="border-slate-200 shadow-sm">
            <CardHeader>
              <CardTitle className="text-lg">Real-Time Verification Webhooks</CardTitle>
              <CardDescription>
                CertVerify AI delivers an HTTP POST request to your server as soon as an asynchronous certificate verification completes.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <form onSubmit={handleSaveWebhook} className="space-y-4 max-w-2xl">
                <div>
                  <Label htmlFor="webhook-url">Webhook Delivery URL (HTTPS)</Label>
                  <Input
                    id="webhook-url"
                    type="url"
                    placeholder="https://api.yourdomain.com/webhooks/certverify"
                    value={webhookUrl}
                    onChange={(e) => setWebhookUrl(e.target.value)}
                    className="mt-1"
                    required
                  />
                  <p className="text-xs text-slate-500 mt-1">Must accept HTTP POST requests with JSON payload.</p>
                </div>

                <div>
                  <Label htmlFor="webhook-secret">HMAC Signing Secret</Label>
                  <Input
                    id="webhook-secret"
                    type="text"
                    placeholder="Auto-generated or custom shared secret"
                    value={webhookSecret}
                    onChange={(e) => setWebhookSecret(e.target.value)}
                    className="mt-1 font-mono text-xs"
                  />
                  <p className="text-xs text-slate-500 mt-1">
                    Used to verify incoming requests via the{' '}
                    <code className="text-xs bg-slate-100 px-1 py-0.5 rounded text-blue-600">X-CertVerify-Signature</code> header.
                  </p>
                </div>

                <div className="flex items-center gap-3 pt-2">
                  <Button type="submit" disabled={savingWebhook} className="bg-blue-600 hover:bg-blue-700">
                    {savingWebhook ? <Loader2 className="h-4 w-4 animate-spin mr-1.5" /> : null}
                    Save Webhook Settings
                  </Button>
                  <Button
                    type="button"
                    variant="outline"
                    onClick={handleTestWebhook}
                    disabled={testingWebhook || !webhookUrl}
                    className="flex items-center gap-1.5"
                  >
                    {testingWebhook ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
                    Send Test Ping
                  </Button>
                </div>

                {testResult && (
                  <div className="p-3 bg-slate-100 border rounded-lg text-xs font-mono text-slate-800">
                    {testResult}
                  </div>
                )}
              </form>
            </CardContent>
          </Card>
        </TabsContent>

        {/* TAB 3: API REFERENCE & QUICKSTART */}
        <TabsContent value="quickstart" className="space-y-6">
          <Card className="border-slate-200 shadow-sm">
            <CardHeader>
              <CardTitle className="text-lg">B2B Headless Verification API</CardTitle>
              <CardDescription>
                Verify certificates programmatically via our high-speed endpoint.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center gap-2">
                <Badge className="bg-blue-600 text-white font-mono">POST</Badge>
                <code className="text-sm font-mono text-slate-800 font-semibold">/api/v1/developer/verify</code>
              </div>

              <div className="flex items-center gap-2 border-b pb-2">
                <Button
                  variant={snippetLang === 'curl' ? 'default' : 'ghost'}
                  size="sm"
                  onClick={() => setSnippetLang('curl')}
                >
                  cURL
                </Button>
                <Button
                  variant={snippetLang === 'python' ? 'default' : 'ghost'}
                  size="sm"
                  onClick={() => setSnippetLang('python')}
                >
                  Python
                </Button>
                <Button
                  variant={snippetLang === 'node' ? 'default' : 'ghost'}
                  size="sm"
                  onClick={() => setSnippetLang('node')}
                >
                  Node.js
                </Button>
              </div>

              <div className="bg-slate-900 rounded-xl p-4 text-slate-100 font-mono text-xs overflow-x-auto relative">
                {snippetLang === 'curl' && (
                  <pre>{`curl -X POST "http://localhost:8000/api/v1/developer/verify" \\
  -H "X-API-Key: cv_live_your_api_key_here" \\
  -F "file=@certificate.pdf"`}</pre>
                )}
                {snippetLang === 'python' && (
                  <pre>{`import requests

url = "http://localhost:8000/api/v1/developer/verify"
headers = {"X-API-Key": "cv_live_your_api_key_here"}

with open("certificate.pdf", "rb") as f:
    response = requests.post(url, headers=headers, files={"file": f})

print("Queued Job:", response.json())`}</pre>
                )}
                {snippetLang === 'node' && (
                  <pre>{`const axios = require('axios');
const fs = require('fs');
const FormData = require('form-data');

const form = new FormData();
form.append('file', fs.createReadStream('certificate.pdf'));

axios.post('http://localhost:8000/api/v1/developer/verify', form, {
  headers: {
    ...form.getHeaders(),
    'X-API-Key': 'cv_live_your_api_key_here'
  }
}).then(res => console.log(res.data));`}</pre>
                )}
              </div>

              <div className="p-3 bg-slate-50 border rounded-lg text-xs text-slate-600 space-y-1">
                <div className="font-semibold text-slate-800">Response (201 Created):</div>
                <pre className="font-mono text-slate-700">{`{
  "certificate_id": "46cb134b-d243-4325-a2ea-561467036c1b",
  "job_id": "081251c6-447a-4e12-abb0-263e83583270",
  "filename": "certificate.pdf",
  "status": "PENDING"
}`}</pre>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
};
