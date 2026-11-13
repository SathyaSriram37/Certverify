import { Component, ErrorInfo, ReactNode } from 'react';
import { AlertTriangle, RotateCcw } from 'lucide-react';
import { Button } from './ui/button';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from './ui/card';

interface Props {
  children?: ReactNode;
}

interface State {
  hasError: boolean;
  error?: Error;
}

export class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
  };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('Uncaught error:', error, errorInfo);
  }

  public render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen flex items-center justify-center p-4 bg-slate-50">
          <Card className="max-w-md w-full border-red-200">
            <CardHeader className="text-center">
              <div className="mx-auto h-12 w-12 rounded-full bg-red-100 flex items-center justify-center text-red-600 mb-2">
                <AlertTriangle className="h-6 w-6" />
              </div>
              <CardTitle className="text-xl text-slate-900">Application Error</CardTitle>
              <CardDescription>
                Something went wrong while executing this component.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <p className="text-xs text-red-600 bg-red-50 p-3 rounded border border-red-200 font-mono overflow-auto max-h-32">
                {this.state.error?.message || 'Unknown runtime error'}
              </p>
            </CardContent>
            <CardFooter>
              <Button
                className="w-full bg-blue-600 hover:bg-blue-700"
                onClick={() => window.location.reload()}
              >
                <RotateCcw className="h-4 w-4 mr-2" />
                Reload Application
              </Button>
            </CardFooter>
          </Card>
        </div>
      );
    }

    return this.props.children;
  }
}

