import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Switch } from '@/components/ui/switch';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Badge } from '@/components/ui/badge';
import { Eye, EyeOff, TestTube, Save, AlertCircle, CheckCircle, Key, Github, Brain } from 'lucide-react';

interface CredentialConfig {
  openai?: {
    enabled: boolean;
    apiKey: string;
    baseUrl: string;
    defaultModel: string;
  };
  anthropic?: {
    enabled: boolean;
    apiKey: string;
    baseUrl: string;
    defaultModel: string;
  };
  ollama?: {
    enabled: boolean;
    baseUrl: string;
    defaultModel: string;
  };
  git?: {
    pat?: {
      enabled: boolean;
      token: string;
      username: string;
    };
    githubApp?: {
      enabled: boolean;
      appId: string;
      installationId: string;
      privateKey: string;
    };
  };
}

interface ValidationStatus {
  [key: string]: {
    valid: boolean;
    message: string;
    tested: boolean;
  };
}

const SettingsPage: React.FC = () => {
  const [config, setConfig] = useState<CredentialConfig>({});
  const [showPasswords, setShowPasswords] = useState<{[key: string]: boolean}>({});
  const [validationStatus, setValidationStatus] = useState<ValidationStatus>({});
  const [isLoading, setIsLoading] = useState(false);
  const [saveStatus, setSaveStatus] = useState<'idle' | 'saving' | 'success' | 'error'>('idle');
  const [errorMessage, setErrorMessage] = useState('');

  useEffect(() => {
    loadCurrentConfig();
  }, []);

  const loadCurrentConfig = async () => {
    try {
      const response = await fetch('/api/v1/settings/credentials');
      if (response.ok) {
        const data = await response.json();
        setConfig(data);
      }
    } catch (error) {
      console.error('Failed to load config:', error);
    }
  };

  const togglePasswordVisibility = (field: string) => {
    setShowPasswords(prev => ({
      ...prev,
      [field]: !prev[field]
    }));
  };

  const updateConfig = (path: string[], value: any) => {
    setConfig(prev => {
      const newConfig = { ...prev };
      let current = newConfig;
      
      for (let i = 0; i < path.length - 1; i++) {
        if (!current[path[i]]) {
          current[path[i]] = {};
        }
        current = current[path[i]];
      }
      
      current[path[path.length - 1]] = value;
      return newConfig;
    });
  };

  const testCredential = async (provider: string, credType?: string) => {
    setIsLoading(true);
    const testKey = credType ? `${provider}_${credType}` : provider;
    
    try {
      const response = await fetch('/api/v1/settings/test-credential', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          provider,
          credType,
          config: provider === 'git' ? config.git : config[provider]
        }),
      });

      const result = await response.json();
      
      setValidationStatus(prev => ({
        ...prev,
        [testKey]: {
          valid: result.success,
          message: result.message || (result.success ? 'Connection successful' : 'Connection failed'),
          tested: true
        }
      }));
    } catch (error) {
      setValidationStatus(prev => ({
        ...prev,
        [testKey]: {
          valid: false,
          message: 'Failed to test connection',
          tested: true
        }
      }));
    } finally {
      setIsLoading(false);
    }
  };

  const saveCredentials = async () => {
    setSaveStatus('saving');
    setErrorMessage('');
    
    try {
      const response = await fetch('/api/v1/settings/credentials', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(config),
      });

      if (response.ok) {
        setSaveStatus('success');
        setTimeout(() => setSaveStatus('idle'), 3000);
      } else {
        const error = await response.json();
        setErrorMessage(error.message || 'Failed to save credentials');
        setSaveStatus('error');
      }
    } catch (error) {
      setErrorMessage('Network error while saving credentials');
      setSaveStatus('error');
    }
  };

  const getValidationBadge = (key: string) => {
    const status = validationStatus[key];
    if (!status?.tested) return null;
    
    return (
      <Badge variant={status.valid ? "default" : "destructive"} className="ml-2">
        {status.valid ? <CheckCircle className="w-3 h-3 mr-1" /> : <AlertCircle className="w-3 h-3 mr-1" />}
        {status.valid ? 'Valid' : 'Invalid'}
      </Badge>
    );
  };

  return (
    <div className="container mx-auto p-6 max-w-4xl">
      <div className="mb-6">
        <h1 className="text-2xl font-bold">TINAA Settings</h1>
        <p className="text-muted-foreground">Configure API keys and credentials for AI providers and Git integration</p>
      </div>

      {saveStatus === 'success' && (
        <Alert className="mb-6">
          <CheckCircle className="h-4 w-4" />
          <AlertDescription>
            Credentials saved successfully and stored securely in Kubernetes secrets
          </AlertDescription>
        </Alert>
      )}

      {saveStatus === 'error' && (
        <Alert variant="destructive" className="mb-6">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>
            {errorMessage}
          </AlertDescription>
        </Alert>
      )}

      <Tabs defaultValue="ai-providers" className="space-y-6">
        <TabsList className="grid w-full grid-cols-2">
          <TabsTrigger value="ai-providers" className="flex items-center gap-2">
            <Brain className="w-4 h-4" />
            AI Providers
          </TabsTrigger>
          <TabsTrigger value="git-auth" className="flex items-center gap-2">
            <Github className="w-4 h-4" />
            Git Authentication
          </TabsTrigger>
        </TabsList>

        <TabsContent value="ai-providers" className="space-y-6">
          {/* OpenAI Configuration */}
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="flex items-center gap-2">
                    <Key className="w-5 h-5" />
                    OpenAI
                    {getValidationBadge('openai')}
                  </CardTitle>
                  <CardDescription>
                    Configure OpenAI API access for GPT models
                  </CardDescription>
                </div>
                <Switch
                  checked={config.openai?.enabled || false}
                  onCheckedChange={(enabled) => updateConfig(['openai', 'enabled'], enabled)}
                />
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="openai-key">API Key</Label>
                  <div className="relative">
                    <Input
                      id="openai-key"
                      type={showPasswords.openaiKey ? "text" : "password"}
                      placeholder="sk-..."
                      value={config.openai?.apiKey || ''}
                      onChange={(e) => updateConfig(['openai', 'apiKey'], e.target.value)}
                      disabled={!config.openai?.enabled}
                    />
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      className="absolute right-0 top-0 h-full px-3"
                      onClick={() => togglePasswordVisibility('openaiKey')}
                      disabled={!config.openai?.enabled}
                    >
                      {showPasswords.openaiKey ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                    </Button>
                  </div>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="openai-model">Default Model</Label>
                  <Input
                    id="openai-model"
                    placeholder="gpt-4"
                    value={config.openai?.defaultModel || 'gpt-4'}
                    onChange={(e) => updateConfig(['openai', 'defaultModel'], e.target.value)}
                    disabled={!config.openai?.enabled}
                  />
                </div>
              </div>
              <div className="space-y-2">
                <Label htmlFor="openai-url">Base URL</Label>
                <Input
                  id="openai-url"
                  placeholder="https://api.openai.com/v1"
                  value={config.openai?.baseUrl || 'https://api.openai.com/v1'}
                  onChange={(e) => updateConfig(['openai', 'baseUrl'], e.target.value)}
                  disabled={!config.openai?.enabled}
                />
              </div>
              <Button
                onClick={() => testCredential('openai')}
                disabled={!config.openai?.enabled || !config.openai?.apiKey || isLoading}
                className="w-full"
              >
                <TestTube className="w-4 h-4 mr-2" />
                Test Connection
              </Button>
            </CardContent>
          </Card>

          {/* Anthropic Configuration */}
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="flex items-center gap-2">
                    <Key className="w-5 h-5" />
                    Anthropic
                    {getValidationBadge('anthropic')}
                  </CardTitle>
                  <CardDescription>
                    Configure Anthropic API access for Claude models
                  </CardDescription>
                </div>
                <Switch
                  checked={config.anthropic?.enabled || false}
                  onCheckedChange={(enabled) => updateConfig(['anthropic', 'enabled'], enabled)}
                />
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="anthropic-key">API Key</Label>
                  <div className="relative">
                    <Input
                      id="anthropic-key"
                      type={showPasswords.anthropicKey ? "text" : "password"}
                      placeholder="sk-ant-..."
                      value={config.anthropic?.apiKey || ''}
                      onChange={(e) => updateConfig(['anthropic', 'apiKey'], e.target.value)}
                      disabled={!config.anthropic?.enabled}
                    />
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      className="absolute right-0 top-0 h-full px-3"
                      onClick={() => togglePasswordVisibility('anthropicKey')}
                      disabled={!config.anthropic?.enabled}
                    >
                      {showPasswords.anthropicKey ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                    </Button>
                  </div>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="anthropic-model">Default Model</Label>
                  <Input
                    id="anthropic-model"
                    placeholder="claude-3-sonnet-20240229"
                    value={config.anthropic?.defaultModel || 'claude-3-sonnet-20240229'}
                    onChange={(e) => updateConfig(['anthropic', 'defaultModel'], e.target.value)}
                    disabled={!config.anthropic?.enabled}
                  />
                </div>
              </div>
              <div className="space-y-2">
                <Label htmlFor="anthropic-url">Base URL</Label>
                <Input
                  id="anthropic-url"
                  placeholder="https://api.anthropic.com"
                  value={config.anthropic?.baseUrl || 'https://api.anthropic.com'}
                  onChange={(e) => updateConfig(['anthropic', 'baseUrl'], e.target.value)}
                  disabled={!config.anthropic?.enabled}
                />
              </div>
              <Button
                onClick={() => testCredential('anthropic')}
                disabled={!config.anthropic?.enabled || !config.anthropic?.apiKey || isLoading}
                className="w-full"
              >
                <TestTube className="w-4 h-4 mr-2" />
                Test Connection
              </Button>
            </CardContent>
          </Card>

          {/* Ollama Configuration */}
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="flex items-center gap-2">
                    <Key className="w-5 h-5" />
                    Ollama (Local)
                    {getValidationBadge('ollama')}
                  </CardTitle>
                  <CardDescription>
                    Configure local Ollama instance for self-hosted models
                  </CardDescription>
                </div>
                <Switch
                  checked={config.ollama?.enabled || false}
                  onCheckedChange={(enabled) => updateConfig(['ollama', 'enabled'], enabled)}
                />
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="ollama-url">Base URL</Label>
                  <Input
                    id="ollama-url"
                    placeholder="http://ollama:11434"
                    value={config.ollama?.baseUrl || 'http://ollama:11434'}
                    onChange={(e) => updateConfig(['ollama', 'baseUrl'], e.target.value)}
                    disabled={!config.ollama?.enabled}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="ollama-model">Default Model</Label>
                  <Input
                    id="ollama-model"
                    placeholder="llama2"
                    value={config.ollama?.defaultModel || 'llama2'}
                    onChange={(e) => updateConfig(['ollama', 'defaultModel'], e.target.value)}
                    disabled={!config.ollama?.enabled}
                  />
                </div>
              </div>
              <Button
                onClick={() => testCredential('ollama')}
                disabled={!config.ollama?.enabled || !config.ollama?.baseUrl || isLoading}
                className="w-full"
              >
                <TestTube className="w-4 h-4 mr-2" />
                Test Connection
              </Button>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="git-auth" className="space-y-6">
          {/* GitHub PAT Configuration */}
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="flex items-center gap-2">
                    <Github className="w-5 h-5" />
                    GitHub Personal Access Token
                    {getValidationBadge('git_pat')}
                  </CardTitle>
                  <CardDescription>
                    Configure GitHub PAT for repository access
                  </CardDescription>
                </div>
                <Switch
                  checked={config.git?.pat?.enabled || false}
                  onCheckedChange={(enabled) => updateConfig(['git', 'pat', 'enabled'], enabled)}
                />
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="git-username">Username</Label>
                  <Input
                    id="git-username"
                    placeholder="git"
                    value={config.git?.pat?.username || 'git'}
                    onChange={(e) => updateConfig(['git', 'pat', 'username'], e.target.value)}
                    disabled={!config.git?.pat?.enabled}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="git-token">Personal Access Token</Label>
                  <div className="relative">
                    <Input
                      id="git-token"
                      type={showPasswords.gitToken ? "text" : "password"}
                      placeholder="ghp_..."
                      value={config.git?.pat?.token || ''}
                      onChange={(e) => updateConfig(['git', 'pat', 'token'], e.target.value)}
                      disabled={!config.git?.pat?.enabled}
                    />
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      className="absolute right-0 top-0 h-full px-3"
                      onClick={() => togglePasswordVisibility('gitToken')}
                      disabled={!config.git?.pat?.enabled}
                    >
                      {showPasswords.gitToken ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                    </Button>
                  </div>
                </div>
              </div>
              <Button
                onClick={() => testCredential('git', 'pat')}
                disabled={!config.git?.pat?.enabled || !config.git?.pat?.token || isLoading}
                className="w-full"
              >
                <TestTube className="w-4 h-4 mr-2" />
                Test GitHub Access
              </Button>
            </CardContent>
          </Card>

          {/* GitHub App Configuration */}
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="flex items-center gap-2">
                    <Github className="w-5 h-5" />
                    GitHub App
                    {getValidationBadge('git_githubApp')}
                  </CardTitle>
                  <CardDescription>
                    Configure GitHub App for enhanced repository access
                  </CardDescription>
                </div>
                <Switch
                  checked={config.git?.githubApp?.enabled || false}
                  onCheckedChange={(enabled) => updateConfig(['git', 'githubApp', 'enabled'], enabled)}
                />
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="github-app-id">App ID</Label>
                  <Input
                    id="github-app-id"
                    placeholder="123456"
                    value={config.git?.githubApp?.appId || ''}
                    onChange={(e) => updateConfig(['git', 'githubApp', 'appId'], e.target.value)}
                    disabled={!config.git?.githubApp?.enabled}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="github-installation-id">Installation ID</Label>
                  <Input
                    id="github-installation-id"
                    placeholder="789012"
                    value={config.git?.githubApp?.installationId || ''}
                    onChange={(e) => updateConfig(['git', 'githubApp', 'installationId'], e.target.value)}
                    disabled={!config.git?.githubApp?.enabled}
                  />
                </div>
              </div>
              <div className="space-y-2">
                <Label htmlFor="github-private-key">Private Key (PEM format)</Label>
                <Textarea
                  id="github-private-key"
                  placeholder="-----BEGIN RSA PRIVATE KEY-----&#10;..."
                  rows={6}
                  value={config.git?.githubApp?.privateKey || ''}
                  onChange={(e) => updateConfig(['git', 'githubApp', 'privateKey'], e.target.value)}
                  disabled={!config.git?.githubApp?.enabled}
                />
              </div>
              <Button
                onClick={() => testCredential('git', 'githubApp')}
                disabled={!config.git?.githubApp?.enabled || !config.git?.githubApp?.appId || !config.git?.githubApp?.privateKey || isLoading}
                className="w-full"
              >
                <TestTube className="w-4 h-4 mr-2" />
                Test GitHub App Access
              </Button>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      <div className="flex justify-end mt-8">
        <Button
          onClick={saveCredentials}
          disabled={saveStatus === 'saving'}
          size="lg"
        >
          <Save className="w-4 h-4 mr-2" />
          {saveStatus === 'saving' ? 'Saving...' : 'Save Credentials'}
        </Button>
      </div>

      <Alert className="mt-6">
        <AlertCircle className="h-4 w-4" />
        <AlertDescription>
          All credentials are encrypted and stored securely as Kubernetes secrets in your cluster namespace. 
          They are never logged or exposed in plain text.
        </AlertDescription>
      </Alert>
    </div>
  );
};

export default SettingsPage;