import { NextRequest, NextResponse } from 'next/server';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export async function GET(request: NextRequest) {
  try {
    const response = await fetch(`${API_URL}/urls`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    const data = await response.json();

    if (!response.ok) {
      return NextResponse.json(data, { status: response.status });
    }

    return NextResponse.json(data);
  } catch (error) {
    console.error('Error fetching URLs from backend:', error);
    return NextResponse.json(
      { detail: 'Failed to connect to backend service' },
      { status: 502 }
    );
  }
}

export async function DELETE(request: NextRequest) {
  try {
    const response = await fetch(`${API_URL}/urls`, {
      method: 'DELETE',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      const data = await response.json();
      return NextResponse.json(data, { status: response.status });
    }

    return NextResponse.json({ message: 'All URLs deleted' });
  } catch (error) {
    console.error('Error deleting URLs from backend:', error);
    return NextResponse.json(
      { detail: 'Failed to connect to backend service' },
      { status: 502 }
    );
  }
}
