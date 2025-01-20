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
import { prisma } from '@/app/lib/prisma';
import { getServerSession } from 'next-auth';
import { authOptions } from '@/app/api/auth/[...nextauth]/options';

/* eslint-disable @typescript-eslint/no-explicit-any */

export async function GET() {
  try {
    // 1. Identify user
    const session = await getServerSession(authOptions);
    if (!session?.user?.email) {
      return NextResponse.json({ error: 'Unauthenticated' }, { status: 401 });
    }
    const userEmail = session.user.email;

    // 2. Find all chats belonging to this user
    const userChats = await prisma.chat.findMany({
      where: {
        userId: userEmail,
      },
      include: {
        messages: {
          include: { tool_calls: true },
        },
      },
    });

    // 3. Transform data into the shape used by ChatApp
    const chatsObj: Record<string, any> = {};

    for (const chat of userChats) {
      chatsObj[chat.id] = {
        title: chat.title,
        messages: chat.messages.map((m) => ({
          id: m.id,
          type: m.type,
          content: m.content,
          name: m.name,
          tool_call_id: m.tool_call_id,
          additional_kwargs: m.additional_kwargs,
          tool_calls: m.tool_calls.map((tc) => ({
            id: tc.id,
            name: tc.name,
            args: tc.args,
          })),
        })),
      };
    }

    return NextResponse.json({ chats: chatsObj });
  } catch (err) {
    console.error('GET /api/chats error:', err);
    return NextResponse.json({ error: 'Failed to load chats.' }, { status: 500 });
  }
}

export async function POST(req: Request) {
  try {
    // 1. Identify user
    const session = await getServerSession(authOptions);
    if (!session?.user?.email) {
      return NextResponse.json({ error: 'Unauthenticated' }, { status: 401 });
    }
    const userEmail = session.user.email;

    // 2. Parse posted chats
    const { chats } = await req.json() as {
      chats: Record<
        string,
        {
          title: string;
          messages: Array<{
            id: string;
            type: string;
            content: string;
            name?: string;
            tool_call_id?: string;
            additional_kwargs?: any;
            tool_calls?: Array<{
              id: string;
              name: string;
              args: any;
            }>;
          }>;
        }
      >;
    };

    // 3. Upsert each chat => must include userId
    for (const [chatId, chatData] of Object.entries(chats)) {
      await prisma.chat.upsert({
        where: { id: chatId },
        create: {
          id: chatId,
          title: chatData.title || 'Untitled Chat',
          userId: userEmail, // <--- store the user's email
        },
        update: {
          title: chatData.title || 'Untitled Chat',
          userId: userEmail, // ensure userId is correct
          updatedAt: new Date(),
        },
      });

      // 4. Upsert each message
      for (const msg of chatData.messages) {
        await prisma.message.upsert({
          where: { id: msg.id },
          create: {
            id: msg.id,
            type: msg.type,
            content: msg.content,
            name: msg.name,
            tool_call_id: msg.tool_call_id,
            additional_kwargs: msg.additional_kwargs,
            chatId: chatId,
          },
          update: {
            type: msg.type,
            content: msg.content,
            name: msg.name,
            tool_call_id: msg.tool_call_id,
            additional_kwargs: msg.additional_kwargs,
            updatedAt: new Date(),
          },
        });

        // 5. Upsert each ToolCall
        if (msg.tool_calls && msg.tool_calls.length > 0) {
          for (const tc of msg.tool_calls) {
            await prisma.toolCall.upsert({
              where: { id: tc.id },
              create: {
                id: tc.id,
                name: tc.name,
                args: tc.args,
                messageId: msg.id,
              },
              update: {
                name: tc.name,
                args: tc.args,
                updatedAt: new Date(),
              },
            });
          }
        }
      }
    }

    return NextResponse.json({ success: true });
  } catch (err) {
    console.error('POST /api/chats error:', err);
    return NextResponse.json({ error: 'Failed to save chats.' }, { status: 500 });
  }
}