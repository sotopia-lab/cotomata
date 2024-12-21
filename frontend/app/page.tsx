"use client"

import { Button } from "@/components/ui/button";
import { useRouter } from "next/navigation";
import { useLoading } from "../context/loading-provider";
import Loading from "./loading";
import Error from "./error";
import { useState } from "react";
import { Sparkles, Code2 } from 'lucide-react';
import { motion } from 'framer-motion';

export default function LandingPage() {
  const router = useRouter();
  const { isReady, error, socket } = useLoading();
  const [isInitializing, setIsInitializing] = useState(false);

  const handleStartSession = () => {
    console.log('Start Session button clicked');
    setIsInitializing(true);
    if (socket) {
      console.log('Emitting init_process event');
      socket.emit('init_process');
    } else {
      console.error('Socket not available');
      setIsInitializing(false);
    }
  };

  if (error) {
    return <Error error={error} reset={() => router.refresh()} />;
  }

  if (isReady) {
    router.push('/workspace');
    return null;
  }

  return (
    <div className="flex min-h-screen flex-col bg-[#0A0A0A]">
      {/* Header */}
      <header className="px-4 lg:px-6 h-14 flex items-center border-b border-white/10">
        <motion.div 
          className="flex items-center space-x-2"
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.5 }}
        >
          <motion.div
            animate={{ 
              rotate: [0, 15, -15, 0],
              scale: [1, 1.2, 1.2, 1]
            }}
            transition={{ 
              duration: 2,
              repeat: Infinity,
              repeatDelay: 4
            }}
          >
            <Sparkles className="h-6 w-6 text-white" />
          </motion.div>
          <span className="font-bold text-white text-lg">Cotomata</span>
        </motion.div>
      </header>

      {/* Main Content */}
      <main className="flex-1 relative flex items-center justify-center -mt-20">
        {/* Background Effects */}
        <motion.div 
          className="absolute inset-0 bg-gradient-to-b from-purple-500/10 to-blue-500/10"
          initial={{ opacity: 0 }}
          animate={{ opacity: 0.5 }}
          transition={{ duration: 1.5 }}
        />
        <div className="absolute inset-0 bg-[url('/grid.svg')] opacity-20" />
        
        {/* Content */}
        <div className="relative px-4 md:px-6 w-full max-w-screen-sm mx-auto">
          <div className="flex flex-col items-center space-y-16 text-center">
            <motion.div 
              className="space-y-6"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.8, delay: 0.2 }}
            >
              <div className="relative">
                <motion.div
                  className="absolute inset-0 blur-3xl opacity-50"
                  animate={{
                    background: [
                      'linear-gradient(45deg, #ff3d00, #0400ff)',
                      'linear-gradient(45deg, #0400ff, #00ff9d)',
                      'linear-gradient(45deg, #00ff9d, #ff3d00)'
                    ]
                  }}
                  transition={{
                    duration: 8,
                    repeat: Infinity,
                    repeatType: "reverse"
                  }}
                />
                <motion.h1 
                  className="text-7xl sm:text-8xl md:text-9xl font-bold tracking-tighter mix-blend-overlay"
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.8, delay: 0.4 }}
                >
                  {/* Split text into individual letters for animation */}
                  {"Cotomata".split("").map((letter, index) => (
                    <motion.span
                      key={index}
                      initial={{ opacity: 0, y: 20 }}
                      animate={{ 
                        opacity: 1, 
                        y: 0,
                        color: ['#ffffff', '#a8b0ff', '#ffffff'],
                        textShadow: [
                          '0 0 20px rgba(255,255,255,0.2)',
                          '0 0 40px rgba(168,176,255,0.3)',
                          '0 0 20px rgba(255,255,255,0.2)'
                        ]
                      }}
                      transition={{
                        duration: 3,
                        delay: 0.5 + index * 0.1,
                        repeat: Infinity,
                        repeatType: "reverse"
                      }}
                      className="inline-block"
                      whileHover={{
                        scale: 1.2,
                        rotate: [-5, 5, 0],
                        transition: { duration: 0.3 }
                      }}
                    >
                      {letter}
                    </motion.span>
                  ))}
                </motion.h1>
              </div>
              <motion.p 
                className="text-2xl sm:text-3xl text-gray-300 font-light"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ duration: 0.8, delay: 1.2 }}
              >
                Research Prototype for Studying Cooperative Agents
              </motion.p>
            </motion.div>
            
            <motion.div 
              className="w-full max-w-md"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.8, delay: 1.4 }}
            >
              {isInitializing ? (
                <div className="space-y-4">
                  <p className="text-lg text-gray-400 text-center animate-pulse">
                    Initializing your development environment...
                  </p>
                  <Loading />
                </div>
              ) : (
                <motion.div
                  whileHover={{ scale: 1.03 }}
                  whileTap={{ scale: 0.98 }}
                >
                  <Button 
                    size="lg"
                    onClick={handleStartSession}
                    className="w-full h-16 bg-white hover:bg-gray-100 text-black text-xl font-medium rounded-2xl shadow-lg"
                  >
                    <Code2 className="mr-3 h-6 w-6" />
                    Start Session
                  </Button>
                </motion.div>
              )}
            </motion.div>
          </div>
        </div>
      </main>
    </div>
  );
}