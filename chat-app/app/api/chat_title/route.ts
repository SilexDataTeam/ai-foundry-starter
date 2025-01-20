/** 
 * Copyright 2025 Silex Data Solutions dba Data Science Technologies, LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

import { NextResponse } from 'next/server';
import { getServerSession } from 'next-auth';
import { authOptions } from '@/app/api/auth/[...nextauth]/options';

export async function POST(req: Request) {
    try {
        const session = await getServerSession(authOptions);
        if (!session?.user?.email) {
            return NextResponse.json({ error: 'Unauthenticated' }, { status: 401 });
        }

        // Get message from request body
        const { message } = await req.json();
        if (!message) {
            return NextResponse.json({ error: 'Message is required' }, { status: 400 });
        }

        const serviceUrl = process.env.SERVICE_URL || 'http://localhost:8000';
        const response = await fetch(`${serviceUrl}generate_chat_title`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${session.access_token}`,
            },
            body: JSON.stringify({
                initial_message: message
            }),
        });

        if (!response.ok) {
            throw new Error(`Service responded with ${response.status}`);
        }

        const data = await response.json();
        return NextResponse.json({ chat_title: data.title });

    } catch (err) {
        console.error('POST /api/chat_title error:', err);
        return NextResponse.json({ error: 'Failed to create chat title.' }, { status: 500 });
    }
}